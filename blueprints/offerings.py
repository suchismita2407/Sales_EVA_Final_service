from flask import Blueprint, jsonify, request

from blueprints.auth import login_required
from db import execute, query_all
from schemas import OfferingCreate

offerings_bp = Blueprint("offerings", __name__, url_prefix="/api")


@offerings_bp.route("/offerings", methods=["GET", "POST"])
@login_required
def offerings():
    if request.method == "GET":
        return jsonify(query_all("SELECT * FROM offerings"))

    try:
        payload = OfferingCreate.model_validate(request.form.to_dict())
    except ValueError as error:
        return jsonify({"error": "invalid_offering", "details": str(error)}), 400

    offering_id = execute(
        "INSERT INTO offerings (name, industry, description) VALUES (?, ?, ?)",
        (payload.name, payload.industry, payload.description),
    )
    return jsonify({"status": "ok", "id": offering_id}), 201
