from types import SimpleNamespace

import pytest

from errors import LLMParseError
from services import rag_service


class FakeCollection:
    def query(self, **_kwargs):
        return {
            "metadatas": [[{"offering_id": 7}]],
            "distances": [[0.82]],
        }


class FakeEmbeddings:
    def embed_query(self, _text):
        return [0.1, 0.2]


class FakeLlm:
    def __init__(self, content):
        self.content = content

    def invoke(self, _prompt):
        return SimpleNamespace(content=self.content)


def test_match_solutions_uses_mocked_services(monkeypatch):
    monkeypatch.setattr(
        rag_service,
        "query_one",
        lambda query, params: (
            {"id": 1, "industry": "Retail", "description": "Analytics", "requirements": "Reports"}
            if "opportunities" in query
            else {"name": "Insights"}
        ),
    )
    monkeypatch.setattr(rag_service, "get_embeddings", lambda: FakeEmbeddings())
    monkeypatch.setattr(
        rag_service,
        "get_llm",
        lambda: FakeLlm('[{"offering_id": 7, "fit_score": 0.9, "explanation": "Good fit"}]'),
    )
    monkeypatch.setattr(rag_service, "offerings_col", FakeCollection())
    monkeypatch.setattr(rag_service, "execute", lambda *args: 1)

    result = rag_service.match_solutions_for_opportunity(1)

    assert result == [
        {
            "offering_id": 7,
            "offering_name": "Insights",
            "score": 90,
            "reason": "Good fit",
        }
    ]


def test_analyze_gaps_raises_typed_error_on_invalid_llm_json(monkeypatch):
    monkeypatch.setattr(
        rag_service,
        "query_one",
        lambda _query, params: {"description": "Details", "requirements": "Needs"},
    )
    monkeypatch.setattr(rag_service, "get_llm", lambda: FakeLlm("not-json"))

    with pytest.raises(LLMParseError, match="invalid"):
        rag_service.analyze_gaps(1, 2)
