# Sales EVA

Sales EVA is a Flask service for matching sales opportunities with solution offerings and generating AI-assisted gap analyses. It uses SQLite for application data, ChromaDB for retrieval, and an OpenAI-compatible LLM endpoint for generation and embeddings.

## Setup

Use Python 3.11 for the supported dependency stack.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

For a reproducible install, use the committed `requirements.lock` instead:

```powershell
python -m pip install -r requirements.lock
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

- `app.py` exposes the Flask pages and JSON API routes.
- `blueprints/auth.py`, `blueprints/pages.py`, and `blueprints/api.py` isolate authentication, page, and read-only API routing.
- `services/rag_service.py` retrieves offerings and asks the LLM to rank matches or analyze gaps.
- `db.py` owns SQLite schema initialization and parameterized query helpers.
- `vector_store.py` owns the ChromaDB collections used by retrieval.
- `services/input_validator.py` blocks common sensitive-data and prompt-injection patterns before persistence or LLM calls.

## Tests

Run the offline suite with:

```powershell
python -m pytest tests -q
```

The tests do not call an external LLM. The Flask route tests require the supported Python 3.11 dependency stack; on incompatible interpreters they are skipped while the database, validator, and upload tests remain runnable. CI also runs Ruff and `pip-audit`.