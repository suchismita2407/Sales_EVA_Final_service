from flask import Blueprint, jsonify, request

from blueprints.auth import login_required
from db import execute, query_one
from services.doc_extractor import extract_text_from_file
from services.llm_service import get_embeddings
from services.rag_service import index_offering
from services.upload_service import save_uploaded_file
from vector_store import offerings_col

uploads_bp = Blueprint("uploads", __name__, url_prefix="/api")


@uploads_bp.post("/upload_document")
@login_required
def upload_document():
    file = request.files.get("file")
    ref_id = request.form.get("ref_id")
    doc_type = request.form.get("type")
    if not file:
        return jsonify({"error": "file_missing"}), 400

    try:
        path = save_uploaded_file(file)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400

    extracted_text = extract_text_from_file(path)
    if not extracted_text:
        return jsonify({"error": "document_unreadable"}), 400

    embeddings = get_embeddings()
    for index, chunk_start in enumerate(range(0, len(extracted_text), 800)):
        chunk = extracted_text[chunk_start : chunk_start + 800]
        if doc_type == "offering":
            offerings_col.add(
                ids=[f"file_{ref_id}_{index}"],
                embeddings=[embeddings.embed_query(chunk)],
                documents=[chunk],
                metadatas=[{"offering_id": ref_id}],
            )

    execute("UPDATE offerings SET artifact_links=? WHERE id=?", (path, ref_id))
    index_offering(query_one("SELECT * FROM offerings WHERE id=?", (ref_id,)))
    return jsonify({"status": "uploaded"})
