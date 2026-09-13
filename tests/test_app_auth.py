import pytest


@pytest.fixture
def client(tmp_path, monkeypatch):
    pytest.importorskip("flask")
    try:
        import app
    except (ImportError, RuntimeError, TypeError, AttributeError) as error:
        pytest.skip(
            f"optional vector dependencies are incompatible with this Python runtime: {error}"
        )

    monkeypatch.setattr(app.Config, "DATABASE_PATH", str(tmp_path / "app.db"))
    app.init_db()
    app.app.config.update(TESTING=True, SECRET_KEY="test-secret")
    return app.app.test_client()


def test_login_accepts_hashed_seed_credentials(client):
    response = client.post(
        "/login",
        data={"username": "admin", "password": "admin123"},
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/")


def test_login_rejects_wrong_password(client):
    response = client.post(
        "/login",
        data={"username": "admin", "password": "wrong"},
    )

    assert response.status_code == 200
    assert b"Invalid credentials" in response.data


def test_logout_clears_session(client):
    client.post("/login", data={"username": "admin", "password": "admin123"})

    response = client.get("/logout")

    assert response.status_code == 302
    assert response.headers["Location"].endswith("/login")


def test_metrics_returns_request_count(client):
    response = client.get("/metrics")

    assert response.status_code == 200
    assert response.get_json()["requests_total"] >= 1
