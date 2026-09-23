# Sales EVA

Sales EVA is a Flask service for matching sales opportunities with solution offerings and generating AI-assisted gap analyses. It uses SQLite for application data, ChromaDB for retrieval, and an OpenAI-compatible LLM endpoint for generation and embeddings.

## Setup

Use Python 3.14 for the supported dependency stack. This repository includes a reproducible dependency lockfile.

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.lock
Copy-Item .env.example .env
```

If you need to refresh dependencies:

```powershell
python -m pip install --upgrade pip-tools
pip-compile --no-index --output-file=requirements.lock requirements.txt
```

Use the project shortcuts for local validation:

```powershell
make install
make test
make lint
make typecheck
```

Set `SECRET_KEY`, `LLM_API_KEY`, `LLM_BASE_URL`, `LLM_MODEL`, and `EMBEDDING_MODEL` in `.env`. Langfuse variables are optional. Never commit `.env` or provider keys.

### Ollama local setup

Install Ollama for Windows from [ollama.com/download](https://ollama.com/download/windows), then open PowerShell and download the models:

```powershell
ollama pull llama3.2:3b
ollama pull nomic-embed-text
ollama serve
```

Keep `ollama serve` running. The default `.env.example` configuration uses Ollama locally and does not require an API key. If you prefer another Ollama model, set `LLM_MODEL` to a model you have pulled. The embedding model must support Ollama's `/v1/embeddings` endpoint.

The development seed creates an `admin` user with password `admin123`. Change or remove this account before deploying.

## Run

```powershell
python app.py
```

Open `http://127.0.0.1:5000`. LLM-backed routes require valid provider configuration; authentication and database operations work without a live LLM.

## Build and test

These commands require no live LLM or Ollama service:

```powershell
python -m compileall -q .
python -m pytest tests -q
```

The test suite uses offline AI fixtures. CI runs the same test command on every push and pull request, with coverage enforcement.

For production or container deployment:

```powershell
docker build -t sales-eva .
docker run --env-file .env -p 5000:5000 sales-eva
```

Or use the private-volume Compose setup:

```powershell
docker compose up --build
```

Compose routes the container to Ollama running on the host through `host.docker.internal`. Start Ollama first with `ollama serve` and pull the models before starting Compose.

`GET /health` checks application and SQLite availability and returns HTTP 503 when the database is unavailable.

## Architecture

- `app.py` boots the Flask app and register the project blueprints.
- `blueprints/auth.py`, `blueprints/pages.py`, and `blueprints/api.py` isolate authentication, page, and read-only API routing.
- `routes/opportunities.py` owns the opportunity API endpoints and is the single source of truth for opportunity workflows.
- `services/rag_service.py` retrieves offerings and asks the LLM to rank matches or analyze gaps.
- `db.py` owns SQLite schema initialization and parameterized query helpers.
- `vector_store.py` owns the ChromaDB collections used by retrieval.
- `services/input_validator.py` blocks common sensitive-data and prompt-injection patterns before persistence or LLM calls.

## Tests

Run the offline suite with:

```powershell
python -m pytest tests -q
```

The suite is fully offline by default. It mocks the LLM and embedding calls in the test fixtures, so no Ollama or external AI provider is required to validate the app. CI also runs Ruff, mypy, and `pip-audit`.

For a local static check:

```powershell
python -m mypy .
```