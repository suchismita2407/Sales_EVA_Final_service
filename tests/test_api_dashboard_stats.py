def test_dashboard_stats_returns_expected_json(authenticated_client, monkeypatch):
    from blueprints import api as api_module

    _app, client = authenticated_client
    monkeypatch.setattr(
        api_module,
        "query_all",
        lambda query: [{"stage": "Proposal"}] if "opportunities" in query else [{"fit_score": 0.8}],
    )

    response = client.get("/api/dashboard_stats")

    assert response.status_code == 200
    assert response.get_json()["active_opportunities"] == 1
    assert response.get_json()["avg_fit_score"] == 80.0
