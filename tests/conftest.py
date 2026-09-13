import pytest


@pytest.fixture
def authenticated_client(tmp_path, monkeypatch):
    try:
        import app
    except (ImportError, RuntimeError, TypeError, AttributeError) as error:
        pytest.skip(f"optional vector dependencies are incompatible: {error}")

    monkeypatch.setattr(app.Config, "DATABASE_PATH", str(tmp_path / "api.db"))
    app.init_db()
    app.app.config.update(TESTING=True, SECRET_KEY="test-secret")
    client = app.app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 1
    return app, client
