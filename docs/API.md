# RiskGuard AI API

This is a thin FastAPI service over the existing saved behavioral assessments
and Phase 12 application Investigator. FastAPI does not own prediction,
behavioral rules, scoring, thresholds, or AI guardrails.

## Run locally

From the project root:

```powershell
.\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

## `GET /health`

Returns:

```json
{"status":"ok"}
```

## `POST /investigate`

Request body:

```json
{"source_row_id":215984}
```

`source_row_id` is a strict integer from 0 through 10,000,000. The service
looks up that ID in the saved Phase 3 assessment; clients cannot provide a
file path, risk score, risk level, ML probability, or behavioral points.

The response contains the application-owned amount, ML probability,
behavioral points, risk score, risk level, triggered rule evidence, and a
structured investigation explanation. `provider_used` and `fallback_used`
identify the Phase 12 path. The response schema is allowlisted with Pydantic;
arbitrary provider fields are not returned.

Example:

```powershell
curl.exe -X POST http://127.0.0.1:8000/investigate `
  -H "Content-Type: application/json" `
  -d '{"source_row_id":215984}'
```

## Errors

- `422`: malformed JSON or invalid request schema
- `404`: no saved assessment for the requested source row
- `413`: request body exceeds the small service limit
- `500`: safe internal application failure

Errors do not expose tracebacks, secrets, filesystem paths, or raw CSV
contents.

## Deterministic fallback and optional AI

The deterministic Investigator remains authoritative. If no provider key is
configured, or the optional guarded provider fails or returns unsafe output,
the endpoint still succeeds with `provider_used: false` and
`fallback_used: true`. The optional provider is reached only through the
existing Phase 12 AI Investigator and guardrails; FastAPI never calls a model
provider directly. AI recommendations are advisory and no actions are
executed.

## Security limitations

This phase does not add authentication, authorization, rate limiting,
PostgreSQL, TLS termination, or deployment configuration. A production
deployment needs those controls, plus monitoring and real behavioral history.
The API reads the existing saved assessment only and never modifies
`data/raw/creditcard.csv`.
