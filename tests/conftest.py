import secrets

import pytest


class OfflineEmbeddings:
    def embed_query(self, _text):
        return [0.0, 0.0]


class OfflineLlm:
    def invoke(self, _prompt):
        return type("Response", (), {"content": "{}"})()


@pytest.fixture
def authenticated_client(tmp_path, monkeypatch):
    try:
        import app
    except (ImportError, RuntimeError, TypeError, AttributeError) as error:
        pytest.skip(f"optional vector dependencies are incompatible: {error}")

    monkeypatch.setattr(app.Config, "DATABASE_PATH", str(tmp_path / "api.db"))
    monkeypatch.setattr("services.llm_service.get_embeddings", lambda: OfflineEmbeddings())
    monkeypatch.setattr("services.llm_service.get_llm", lambda: OfflineLlm())
    app.init_db()
    app.app.config.update(TESTING=True, SECRET_KEY=secrets.token_urlsafe(32))
    client = app.app.test_client()
    with client.session_transaction() as session:
        session["user_id"] = 1
    return app, client
