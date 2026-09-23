import json
import os
import re

from flask import Blueprint, jsonify, request, send_file, send_from_directory

from blueprints.auth import login_required
from db import execute, query_all, query_one
from services.opportunity_service import (
    build_chat_prompt,
    build_executive_summary,
    collect_retrieved_documents,
    extract_llm_json,
    validate_chat_query,
    validate_opportunity_payload,
)
from services.rag_service import analyze_gaps, index_opportunity, match_solutions_for_opportunity
from services.report_service import generate_gap_pdf
from services.upload_service import save_uploaded_file

bp = Blueprint("opportunities", __name__)


@bp.post("/api/create_opportunity")
@login_required
def api_create_opportunity():
    data = request.get_json(silent=True) or {}
    try:
        cleaned = validate_opportunity_payload(data)
    except ValueError as error:
        return jsonify({"error": "invalid_opportunity", "details": str(error)}), 400

    opp_id = execute(
        """
        INSERT INTO opportunities(name, client, industry, value, stage, description, requirements)
        VALUES(?,?,?,?,?,?,?)
        """,
        (
            cleaned["name"],
            cleaned["client"],
            cleaned["industry"],
            cleaned["value"],
            cleaned["stage"],
            cleaned["description"],
            cleaned["requirements"],
        ),
    )

    opportunity = query_one("SELECT * FROM opportunities WHERE id=?", (opp_id,))
    try:
        index_opportunity(opportunity)
    except (RuntimeError, ValueError, OSError):
        pass

    return jsonify({"status": "created", "id": opp_id, "redirect": "/"}), 200


@bp.post("/api/match_solutions")
@login_required
def api_match_solutions():
    opp_id = request.get_json(silent=True, force=True).get("opportunity_id")
    return jsonify(match_solutions_for_opportunity(opp_id)), 200


@bp.get("/api/opportunity_summary")
@login_required
def api_opportunity_summary():
    opp_id = request.args.get("opportunity_id")
    if not opp_id:
        return jsonify({"error": "Missing opportunity_id"}), 400

    opportunity = query_one("SELECT * FROM opportunities WHERE id = ?", (int(opp_id),))
    if not opportunity:
        return jsonify({"error": "Opportunity not found"}), 404

    recommendations = query_all(
        "SELECT fit_score FROM recommendations WHERE opportunity_id = ? ORDER BY created_at DESC",
        (int(opp_id),),
    )
    summary = build_executive_summary(
        opportunity,
        [{"score": row["fit_score"]} for row in recommendations if row.get("fit_score") is not None],
    )
    return jsonify(summary)


@bp.post("/api/save_feedback")
@login_required
def api_save_feedback():
    data = request.get_json(silent=True) or {}
    opp_id = data.get("opportunity_id")
    offering_id = data.get("offering_id")
    rating = data.get("rating")
    comments = data.get("comments", "")

    if not opp_id or not offering_id:
        return jsonify({"error": "missing opportunity or offering"}), 400

    execute(
        "INSERT INTO feedback(opportunity_id, offering_id, rating, comments) VALUES (?,?,?,?)",
        (opp_id, offering_id, rating, comments),
    )
    return jsonify({"status": "saved"})


@bp.post("/api/analyze_gaps")
@login_required
def api_analyze_gaps():
    data = request.get_json(silent=True) or {}
    opp_id = data.get("opportunity_id")
    off_id = data.get("offering_id")

    if not opp_id or not off_id:
        return jsonify({"error": "Missing opportunity_id or offering_id"}), 400

    return jsonify(analyze_gaps(opp_id, off_id)), 200


@bp.route("/download_gap_report")
@login_required
def download_gap_report():
    opp_id = request.args.get("opp_id")
    off_id = request.args.get("offering_id")
    pdf_path = generate_gap_pdf(int(opp_id), int(off_id))
    return send_file(pdf_path, as_attachment=True)


@bp.route("/api/case_studies")
@login_required
def api_case_studies():
    from services.llm_service import get_embeddings
    from vector_store import case_studies_col

    industry = request.args.get("industry")
    if not industry:
        return jsonify([]), 200

    query_vec = get_embeddings().embed_query(f"case study for {industry} industry")
    results = case_studies_col.query(query_embeddings=[query_vec], n_results=5)

    metadata = results.get("metadatas", [])[0] if results.get("metadatas") else []
    if not metadata:
        return jsonify([]), 200

    items = []
    for meta in metadata:
        case_id = meta.get("id")
        if not case_id:
            continue
        row = query_one("SELECT * FROM case_studies WHERE id=?", (case_id,))
        if row:
            items.append(
                {
                    "id": row["id"],
                    "title": row["title"],
                    "industry": row["industry"],
                    "key_benefit": row.get("benefit") or "Not Available",
                    "file_link": os.path.basename(row.get("link")) if row.get("link") else "",
                }
            )
    return jsonify(items), 200


@bp.post("/api/upload_case")
@login_required
def api_upload_case():
    from services.doc_extractor import extract_text_from_file
    from services.llm_service import get_embeddings, get_llm
    from vector_store import case_studies_col

    file = request.files.get("file")
    if not file:
        return jsonify({"error": "File missing"}), 400

    try:
        file_path = save_uploaded_file(file)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    extracted_text = extract_text_from_file(file_path) or ""
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
    raw = getattr(reply, "content", str(reply))
    data = extract_llm_json(
        raw,
        {"title": file.filename, "industry": "General", "key_benefit": "Insights Not Extracted"},
    )

    relative_path = os.path.join("uploads", os.path.basename(file_path))
    case_id = execute(
        "INSERT INTO case_studies(title, industry, benefit, link) VALUES (?,?,?,?)",
        (
            data.get("title", file.filename),
            data.get("industry", "General"),
            data.get("key_benefit", "Insights Not Extracted"),
            relative_path,
        ),
    )

    vec = get_embeddings().embed_query(extracted_text[:1500])
    case_studies_col.add(
        ids=[f"case-{case_id}"],
        embeddings=[vec],
        documents=[extracted_text],
        metadatas=[{"id": case_id, "title": data.get("title", file.filename), "industry": data.get("industry", "General")}],
    )
    return jsonify({"status": "saved", "id": case_id})


@bp.route("/uploads/<path:filename>")
def uploaded_file(filename):
    upload_path = os.path.join(os.getcwd(), "uploads")
    return send_from_directory(upload_path, filename)


@bp.post("/api/chat")
@login_required
def chatbot_api():
    from services.llm_service import get_embeddings, tracked_llm_call
    from vector_store import case_studies_col, offerings_col

    data = request.get_json(force=True)
    user_query = (data.get("query") or "").strip().lower()

    is_valid, validation_error = validate_chat_query(user_query)
    if not is_valid:
        if validation_error and validation_error.startswith("<p>"):
            return jsonify({"answer": validation_error, "format": "html"})
        return jsonify({"answer": validation_error})

    if any(user_query.startswith(k) for k in ["hi", "hello", "hey", "how are you", "good morning", "good evening", "good afternoon", "who are you", "what is your name"]):
        return jsonify({"answer": "Hello! How can I support you with opportunities, offerings or case studies?"})

    if any(q in user_query for q in ["what is ai", "what is cloud", "define", "explain", "difference between", "compare", "what do you think"]):
        return jsonify({"answer": "I can answer about offerings, case studies and opportunities. Ask about solution fit, industry trends, client needs, or opportunities."})

    query_vec = get_embeddings().embed_query(user_query)
    offers_res = offerings_col.query(query_embeddings=[query_vec], n_results=4)
    cases_res = case_studies_col.query(query_embeddings=[query_vec], n_results=4)

    kb_context = "\n\n".join(
        collect_retrieved_documents(offers_res, "OFFERING")
        + collect_retrieved_documents(cases_res, "CASE_STUDY")
    )

    prompt = build_chat_prompt(user_query, kb_context)

    answer = tracked_llm_call(prompt)
    return jsonify({"answer": answer, "format": "html"})
