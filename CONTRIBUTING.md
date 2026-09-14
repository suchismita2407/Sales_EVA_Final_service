# Contributing

## Development setup

1. Use Python 3.11.
2. Create a virtual environment and install `requirements.lock`.
3. Copy `.env.example` to `.env` and configure Ollama or another OpenAI-compatible endpoint.

## Before opening a change

Run:

```powershell
python -m pip check
ruff check .
ruff format --check .
python -m pytest tests -q --cov=. --cov-fail-under=60
```

Keep changes focused. Add or update tests with every behavior change. Do not commit `.env`, provider keys, SQLite runtime data, ChromaDB data, uploads, or generated reports.

Use conventional commit prefixes such as `feat:`, `fix:`, `test:`, `docs:`, `refactor:`, and `chore:`.
