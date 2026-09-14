def test_offering_creation_validates_and_persists(authenticated_client):
    _app, client = authenticated_client

    response = client.post(
        "/api/offerings",
        data={"name": "Analytics", "industry": "Retail", "description": "Reports"},
    )

    assert response.status_code == 201
    assert response.get_json()["id"] == 1


def test_offering_creation_rejects_missing_fields(authenticated_client):
    _app, client = authenticated_client

    response = client.post("/api/offerings", data={"name": "Analytics"})

    assert response.status_code == 400
    assert response.get_json()["error"] == "invalid_offering"
