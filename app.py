import json
import logging
import os
import re
import sqlite3
import uuid

from flask import (
    Flask,
    has_request_context,
    jsonify,
    request,
    send_file,
    send_from_directory,
)

from blueprints.api import api_bp
from blueprints.auth import auth_bp, login_required
from blueprints.pages import pages_bp
from config import Config
from db import execute, init_db, query_all, query_one
from errors import AppError, DatabaseUnavailableError
from services.doc_extractor import extract_text_from_file
from services.input_validator import contains_prompt_injection, contains_sensitive_data
from services.llm_service import get_embeddings
from services.rag_service import (
    analyze_gaps,
    index_offering,
    index_opportunity,
    match_solutions_for_opportunity,
)
from services.report_service import generate_gap_pdf
from services.upload_service import save_uploaded_file
from vector_store import offerings_col

app = Flask(__name__)
app.config.from_object(Config)
app.register_blueprint(auth_bp)
app.register_blueprint(api_bp)
app.register_blueprint(pages_bp)
app.logger.setLevel(logging.INFO)
request_count = 0


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "level": record.levelname,
            "message": record.getMessage(),
            "logger": record.name,
            "request_id": getattr(record, "request_id", None),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload)


class RequestContextFilter(logging.Filter):
    def filter(self, record):
        if has_request_context():
            record.request_id = getattr(request, "request_id", None)
        return True


for handler in app.logger.handlers:
    handler.setFormatter(JsonFormatter())
    handler.addFilter(RequestContextFilter())


@app.before_request
def assign_request_id():
    global request_count
    request_count += 1
    request.request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))


@app.after_request
def add_request_id(response):
    response.headers["X-Request-ID"] = request.request_id
    return response


UPLOAD_DIR = os.path.abspath("uploads")


@app.after_request
def add_security_headers(response):
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "SAMEORIGIN")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    return response


@app.errorhandler(413)
def request_too_large(_error):
    return jsonify({"error": "Uploaded content exceeds the size limit"}), 413


@app.errorhandler(AppError)
def handle_app_error(error):
    app.logger.warning("Application request failed", extra={"error_code": error.error_code})
    return jsonify({"error": error.error_code, "message": str(error)}), error.status_code


@app.get("/health")
def health():
    try:
        query_one("SELECT 1")
        return jsonify({"status": "ok", "database": "ok"})
    except sqlite3.Error as error:
        app.logger.exception("Health check failed")
        raise DatabaseUnavailableError("Database is unavailable") from error


@app.get("/metrics")
def metrics():
    return jsonify({"requests_total": request_count})


with app.app_context():
    init_db()


# ====================== CREATE OFFERING FIXED =========================


@app.route("/api/offerings", methods=["GET", "POST"])
@login_required
def api_offerings():
    if request.method == "GET":
        data = query_all("SELECT * FROM offerings")
        return jsonify(data)

    # ---------- CREATE OFFERING ----------
    name = request.form.get("name")
    industry = request.form.get("industry")
    description = request.form.get("description", "")

    offering_id = execute(
        "INSERT INTO offerings (name, industry, description) VALUES (?, ?, ?)",
        (name, industry, description),
    )

    return jsonify({"status": "ok", "id": offering_id})


# ======================================================================


@app.route("/api/upload_document", methods=["POST"])
@login_required
def api_upload_document():
    file = request.files.get("file")
    ref_id = request.form.get("ref_id")
    doc_type = request.form.get("type")

    if not file:
        return jsonify({"error": "file missing"}), 400

    try:
        path = save_uploaded_file(file)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    extracted_text = extract_text_from_file(path)

    if not extracted_text:
        return jsonify({"error": "Unable to read document"}), 400

    chunks = [extracted_text[i : i + 800] for i in range(0, len(extracted_text), 800)]
    emb = get_embeddings()

    for idx, chunk in enumerate(chunks):
        vec = emb.embed_query(chunk)

        if doc_type == "offering":
            offerings_col.add(
                ids=[f"file_{ref_id}_{idx}"],
                embeddings=[vec],
                documents=[chunk],
                metadatas=[{"offering_id": ref_id}],
            )

    execute("UPDATE offerings SET artifact_links=? WHERE id=?", (path, ref_id))

    # re-index after upload
    data = query_one("SELECT * FROM offerings WHERE id=?", (ref_id,))
    index_offering(data)

    return jsonify({"status": "uploaded"})


@app.post("/api/create_opportunity")
@login_required
def api_create_opportunity():
    from services.input_validator import (
        contains_prompt_injection,
        contains_sensitive_data,
    )

    data = request.get_json(silent=True) or {}

    # Validate required fields
    required_fields = [
        "name",
        "client",
        "industry",
        "value",
        "stage",
        "description",
        "requirements",
    ]
    for f in required_fields:
        if not data.get(f):
            return jsonify({"error": f"❌ '{f}' is required"}), 400

    # 🚨 Check for sensitive or personal information
    for label, field_value in data.items():
        if isinstance(field_value, str):
            if contains_sensitive_data(field_value):
                return jsonify(
                    {"error": f"⚠️ Personal/Confidential information is not allowed in '{label}'."}
                ), 400

            if contains_prompt_injection(field_value):
                return jsonify(
                    {"error": f"⚠️ Your entry in '{label}' contains unsafe instructions."}
                ), 400

    # ✔ Insert record safely
    try:
        opp_id = execute(
            """
                INSERT INTO opportunities(
                    name, client, industry, value, stage, description, requirements
                )
                VALUES(?,?,?,?,?,?,?)
                """,
            (
                data["name"],
                data["client"],
                data["industry"],
                data["value"],
                data["stage"],
                data["description"],
                data["requirements"],
            ),
        )
    except sqlite3.Error:
        app.logger.exception("Opportunity creation failed")
        return jsonify({"error": "❌ Failed to create opportunity"}), 500

    # Fetch inserted record and add into vector DB
    opp_row = query_one("SELECT * FROM opportunities WHERE id=?", (opp_id,))
    try:
        index_opportunity(opp_row)
    except (RuntimeError, ValueError, OSError):
        app.logger.exception("Opportunity indexing failed", extra={"opportunity_id": opp_id})

    return jsonify({"status": "created", "id": opp_id, "redirect": "/"}), 200


@app.post("/api/match_solutions")
@login_required
def api_match_solutions():
    data = request.get_json(silent=True) or {}
    opp_id = data.get("opportunity_id")

    matches = match_solutions_for_opportunity(opp_id)
    return jsonify(matches), 200


@app.post("/api/save_feedback")
@login_required
def api_save_feedback():
    data = request.get_json(silent=True) or {}

    opp = data.get("opportunity_id")
    off = data.get("offering_id")
    rating = data.get("rating")
    comments = data.get("comments", "")

    if not opp or not off:
        return jsonify({"error": "missing opportunity or offering"}), 400

    execute(
        """
        INSERT INTO feedback(opportunity_id, offering_id, rating, comments)
        VALUES (?,?,?,?)
    """,
        (opp, off, rating, comments),
    )

    return jsonify({"status": "saved"})


@app.post("/api/analyze_gaps")
@login_required
def api_analyze_gaps():
    data = request.get_json(silent=True) or {}
    opp_id = data.get("opportunity_id")
    off_id = data.get("offering_id")

    if not opp_id or not off_id:
        return jsonify({"error": "Missing opportunity_id or offering_id"}), 400

    result = analyze_gaps(opp_id, off_id)
    return jsonify(result), 200


@app.route("/download_gap_report")
@login_required
def download_gap_report():
    opp_id = request.args.get("opp_id")
    off_id = request.args.get("offering_id")

    # Generate a fresh PDF every time user clicks
    pdf_path = generate_gap_pdf(int(opp_id), int(off_id))

    return send_file(pdf_path, as_attachment=True)


# -------- CASE STUDIES (RAG + DB) --------


@app.route("/api/case_studies")
@login_required
def api_case_studies():
    from services.llm_service import get_embeddings
    from vector_store import case_studies_col

    industry = request.args.get("industry")
    if not industry:
        return jsonify([]), 200

    emb = get_embeddings()

    # Query embedding based on industry text
    query_vec = emb.embed_query(f"case study for {industry} industry")

    # Retrieve nearest documents
    res = case_studies_col.query(query_embeddings=[query_vec], n_results=5)

    results = []

    # Validate structure
    if "metadatas" not in res or not res["metadatas"] or not res["metadatas"][0]:
        return jsonify(results), 200

    # Loop over matched metadata
    for meta in res["metadatas"][0]:
        case_id = meta.get("id")
        if not case_id:
            continue

        row = query_one("SELECT * FROM case_studies WHERE id=?", (case_id,))
        if not row:
            continue

        # safe extraction
        benefit = row.get("benefit") or "Not Available"
        link = row.get("link") or ""

        results.append(
            {
                "id": row["id"],
                "title": row["title"],
                "industry": row["industry"],
                "key_benefit": benefit,
                "file_link": os.path.basename(link) if link else "",
            }
        )

    return jsonify(results), 200


# -------- UPLOAD CASE STUDY (LLM + KB) --------
@app.post("/api/upload_case")
@login_required
def api_upload_case():
    app.logger.info("Case study upload started")

    # Receive file
    file = request.files.get("file")
    if not file:
        app.logger.warning("Case study upload missing file")
        return jsonify({"error": "File missing"}), 400

    # Save file
    try:
        file_path = save_uploaded_file(file)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    app.logger.info("Case study file saved")

    # extract text
    extracted_text = extract_text_from_file(file_path) or ""
    app.logger.info("Case study text extracted", extra={"text_length": len(extracted_text)})

    from services.llm_service import get_llm

    llm = get_llm()

    prompt = f"""
Return ONLY JSON. Do not include markdown, comments, explanation.
Extract data strictly in this JSON format:

{{
  "title": "",
  "industry": "",
  "key_benefit": ""
}}

### DOCUMENT ###
{extracted_text[:1500]}
"""

    reply = llm.invoke(prompt)

    # Catch failure cases
    raw = getattr(reply, "content", str(reply))
    # Clean formatted json
    raw = raw.replace("```json", "").replace("```", "").strip()

    try:
        json_match = re.search(r"\{[\s\S]*\}", raw)
        if json_match:
            data = json.loads(json_match.group(0))
        else:
            raise ValueError("LLM did not return valid JSON")
    except (json.JSONDecodeError, ValueError):
        app.logger.warning("LLM case study response was not valid JSON")
        data = {
            "title": file.filename,
            "industry": "General",
            "key_benefit": "Insights Not Extracted",
        }

    # Build relative path for frontend usage /uploads/<file>
    relative_path = os.path.join("uploads", os.path.basename(file_path))
    case_id = execute(
        """
        INSERT INTO case_studies(title, industry, benefit, link)
        VALUES (?,?,?,?)
    """,
        (
            data.get("title", file.filename),
            data.get("industry", "General"),
            data.get("key_benefit", "Insights Not Extracted"),
            relative_path,
        ),
    )

    # Insert into vector DB
    from services.llm_service import get_embeddings
    from vector_store import case_studies_col

    emb = get_embeddings()
    vec = emb.embed_query(extracted_text[:1500])

    case_studies_col.add(
        ids=[f"case-{case_id}"],
        embeddings=[vec],
        documents=[extracted_text],
        metadatas=[
            {
                "id": case_id,
                "title": data.get("title", file.filename),
                "industry": data.get("industry", "General"),
            }
        ],
    )

    app.logger.info("Case study processing complete", extra={"case_id": case_id})

    return jsonify({"status": "saved", "id": case_id})


# -------- SERVE UPLOADED FILES --------


@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    upload_path = os.path.join(os.getcwd(), "uploads")
    return send_from_directory(upload_path, filename)


@app.post("/api/chat")
@login_required
def chatbot_api():
    from services.llm_service import (
        get_embeddings,
        tracked_llm_call,  # NEW IMPORT
    )
    from vector_store import case_studies_col, offerings_col

    data = request.get_json(force=True)
    user_query = (data.get("query") or "").strip().lower()

    if not user_query:
        return jsonify({"answer": "Please type something."})

    # 🚫 Block Personal Data Leakage
    if contains_sensitive_data(user_query):
        return jsonify(
            {
                "answer": "<p>Please do not enter personal or confidential information "
                "such as phone numbers, email, Aadhaar, PAN etc.</p>",
                "format": "html",
            }
        )

    # 🚫 Block Prompt Injection attempts
    if contains_prompt_injection(user_query):
        return jsonify(
            {
                "answer": "<p>Your query contains unsafe instructions. I cannot proceed.</p>",
                "format": "html",
            }
        )

    # 1) 🔍 Detect casual greeting
    smalltalk_keywords = [
        "hi",
        "hello",
        "hey",
        "how are you",
        "good morning",
        "good evening",
        "good afternoon",
        "who are you",
        "what is your name",
    ]
    if any(user_query.startswith(k) for k in smalltalk_keywords):
        return jsonify(
            {
                "answer": "Hello! How can I support you with opportunities, "
                "offerings or case studies?"
            }
        )

    # 2) Generic questions filter
    general_questions = [
        "what is ai",
        "what is cloud",
        "define",
        "explain",
        "difference between",
        "compare",
        "what do you think",
    ]
    if any(q in user_query for q in general_questions):
        return jsonify(
            {
                "answer": "I can answer about offerings, case studies and opportunities. "
                "Ask about solution fit, industry trends, client needs, or opportunities."
            }
        )

    emb = get_embeddings()

    query_vec = emb.embed_query(user_query)

    # FETCH FROM RAG SOURCES
    offers_res = offerings_col.query(query_embeddings=[query_vec], n_results=4)
    cases_res = case_studies_col.query(query_embeddings=[query_vec], n_results=4)

    def collect_docs(res, label):
        docs = []
        if res.get("documents"):
            for d in res["documents"][0]:
                if d:
                    docs.append(f"[{label}] {d}")
        return docs

    offering_docs = collect_docs(offers_res, "OFFERING")
    case_docs = collect_docs(cases_res, "CASE_STUDY")

    kb_context = "\n\n".join(offering_docs + case_docs)

    # BUILD PROMPT
    if kb_context:
        prompt = f"""
Respond ONLY using HTML format.

<div class="eva-block">

<h3>🔍 Summary</h3>
<p>2-3 sentences answer</p>

<h3>🧩 Recommended Offerings</h3>
<ul>
</ul>

<h3>📚 Relevant Case Studies</h3>
<table border="1" cellspacing="0" cellpadding="4">
<tr><th>Case</th><th>Benefit</th></tr>
</table>

<h3>💼 Business Impact</h3>
<ul>
</ul>

</div>

User Query:
{user_query}

Use ONLY this info:
{kb_context}
"""
    else:
        prompt = f"""
You are EVA, enterprise assistant.
No relevant KB found.

Ask user to mention:

User Query:
{user_query}
"""

    # ✨ Langfuse tracked call
    answer = tracked_llm_call(prompt)

    return jsonify({"answer": answer, "format": "html"})


if __name__ == "__main__":
    app.run(debug=True)
