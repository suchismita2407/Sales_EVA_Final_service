from io import BytesIO


def test_upload_rejects_missing_file(authenticated_client):
    _app, client = authenticated_client

    response = client.post("/api/upload_document", data={"ref_id": "1", "type": "offering"})

    assert response.status_code == 400
    assert response.get_json()["error"] == "file_missing"


def test_upload_rejects_unsupported_file(authenticated_client):
    _app, client = authenticated_client

    response = client.post(
        "/api/upload_document",
        data={"file": (BytesIO(b"bad"), "payload.exe"), "ref_id": "1", "type": "offering"},
        content_type="multipart/form-data",
    )

    assert response.status_code == 400
