from services.opportunity_service import build_executive_summary


def test_executive_summary_has_sales_ready_metrics():
    summary = build_executive_summary(
        {"name": "Cloud transformation", "value": "$5M", "stage": "Proposal"},
        [{"score": 86}, {"score": 74}],
    )

    assert summary["fit_score"] == 80
    assert summary["readiness_score"] >= 70
    assert "headline" in summary
    assert "next_action" in summary


def test_opportunity_summary_api_returns_readiness(authenticated_client):
    _app, client = authenticated_client

    import db

    opp_id = db.execute(
        "INSERT INTO opportunities(name, client, industry, value, stage, description, requirements) VALUES (?,?,?,?,?,?,?)",
        (
            "AI modernization",
            "Atlas Bank",
            "BFSI",
            "$3.2M",
            "Proposal",
            "Need faster analytics and safer data handling.",
            "Cloud migration, AI automation, governance",
        ),
    )

    db.execute(
        "INSERT INTO recommendations(opportunity_id, offering_id, fit_score, explanation) VALUES (?,?,?,?)",
        (opp_id, 1, 0.82, "Strong cloud fit"),
    )

    response = client.get(f"/api/opportunity_summary?opportunity_id={opp_id}")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["readiness_score"] >= 0
    assert payload["next_action"]
