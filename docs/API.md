# API Reference

All protected endpoints require a logged-in session unless noted otherwise. JSON errors use an `error` code and a human-readable `message` or `details` field.

## Public endpoints

### `GET /health`

Returns database readiness:

```json
{"status":"ok","database":"ok"}
```

### `GET /metrics`

Returns the process-local request counter:

```json
{"requests_total": 12}
```

### `POST /login`

Form fields: `username`, `password`. Redirects to `/` on success and renders the login page with an error on failure.

### `GET /logout`

Clears the session and redirects to `/login`.

## Opportunity and offering APIs

### `GET /api/opportunities`

Optional query parameters: `industry`, `stage`. Returns opportunity records with the latest normalized `fit_score` percentage.

### `GET /api/opportunities/<id>`

Returns one opportunity with its latest `fit_score`, or `404` when missing.

### `GET /api/dashboard_stats`

Returns `active_opportunities`, `avg_fit_score`, and `proposal_stage_count`.

### `POST /api/create_opportunity`

JSON body:

```json
{
  "name":"Retail rollout",
  "client":"Example Client",
  "industry":"Retail",
  "value":"500000",
  "stage":"Proposal",
  "description":"Analytics modernization",
  "requirements":"Dashboards and reporting"
}
```

Fields are schema-validated and screened for sensitive data and prompt injection.

### `GET /api/offerings`

Returns all offerings.

### `POST /api/offerings`

Form fields: `name`, `industry`, optional `description`. Returns `201` and the created offering ID.

## Upload and analysis APIs

### `POST /api/upload_document`

Multipart fields: `file`, `ref_id`, `type`. Supported file extensions are PDF, DOCX, and TXT. The default upload limit is 10 MB.

### `POST /api/upload_case`

Multipart field: `file`. Extracts and indexes a case study using the configured LLM and embeddings provider.

### `POST /api/match_solutions`

JSON body: `{"opportunity_id": 1}`. Returns ranked offering matches.

### `POST /api/analyze_gaps`

JSON body: `{"opportunity_id": 1, "offering_id": 2}`. Returns covered, partial, and missing requirements.

### `GET /download_gap_report?opp_id=1&offering_id=2`

Generates and downloads a PDF gap report.
