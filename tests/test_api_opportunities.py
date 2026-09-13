def test_dashboard_stats_returns_normalized_summary(authenticated_client, monkeypatch):
    _app, client = authenticated_client
    from blueprints import api as api_module

    monkeypatch.setattr(
        api_module,
        "query_all",
        lambda query: [{"stage": "Proposal"}] if "opportunities" in query else [{"fit_score": 80}],
    )

    response = client.get("/api/dashboard_stats")

    assert response.status_code == 200
    assert response.get_json() == {
        "active_opportunities": 1,
        "avg_fit_score": 80.0,
        "proposal_stage_count": 1,
    }


def test_opportunities_filters_and_normalizes_latest_score(authenticated_client, monkeypatch):
    _app, client = authenticated_client
    from blueprints import api as api_module

    monkeypatch.setattr(
        api_module,
        "query_all",
        lambda query, params=(): [
            {"id": 4, "name": "Retail rollout", "industry": params[0], "stage": params[1]}
        ],
    )
    monkeypatch.setattr(api_module, "query_one", lambda _query, _params: {"fit_score": 0.75})

    response = client.get("/api/opportunities?industry=Retail&stage=Proposal")

    assert response.status_code == 200
    assert response.get_json()[0]["fit_score"] == 75
