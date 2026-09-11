from flask import Blueprint, jsonify, request

from blueprints.auth import login_required
from db import query_all, query_one
from services.scoring import normalize_score, percentage_score

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.get("/dashboard_stats")
@login_required
def dashboard_stats():
    opportunities = query_all("SELECT * FROM opportunities")
    scores = query_all("""
        SELECT fit_score FROM recommendations
        WHERE fit_score IS NOT NULL
    """)
    normalized_scores = [normalize_score(row["fit_score"]) for row in scores]
    return jsonify({
        "active_opportunities": len(opportunities),
        "avg_fit_score": round(sum(normalized_scores) / len(normalized_scores) * 100, 1)
        if normalized_scores else 0.0,
        "proposal_stage_count": sum(
            opportunity["stage"] == "Proposal" for opportunity in opportunities
        ),
    })


@api_bp.get("/opportunities")
@login_required
def opportunities():
    clauses = []
    params = []
    for field in ("industry", "stage"):
        value = request.args.get(field)
        if value:
            clauses.append(f"{field}=?")
            params.append(value)

    query = "SELECT * FROM opportunities"
    if clauses:
        query += " WHERE " + " AND ".join(clauses)

    results = []
    for opportunity in query_all(query, tuple(params)):
        latest = query_one("""
            SELECT fit_score FROM recommendations
            WHERE opportunity_id = ?
            ORDER BY created_at DESC LIMIT 1
        """, (opportunity["id"],))
        opportunity["fit_score"] = percentage_score(latest["fit_score"]) if latest else 0
        results.append(opportunity)
    return jsonify(results)


@api_bp.get("/opportunities/<int:opp_id>")
@login_required
def opportunity_detail(opp_id):
    opportunity = query_one("SELECT * FROM opportunities WHERE id = ?", (opp_id,))
    if not opportunity:
        return jsonify({"error": "not found"}), 404

    latest = query_one("""
        SELECT fit_score FROM recommendations
        WHERE opportunity_id = ?
        ORDER BY created_at DESC LIMIT 1
    """, (opp_id,))
    opportunity["fit_score"] = percentage_score(latest["fit_score"], digits=1) if latest else 0
    return jsonify(opportunity)