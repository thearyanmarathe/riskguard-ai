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

`/health` is public and does not require authentication.

## Authentication

All investigation endpoints require the application key configured through
the `RISKGUARD_API_KEY` environment variable:

```powershell
$env:RISKGUARD_API_KEY = "local-development-key"
```

Send it in the `X-API-Key` header. Missing or incorrect keys receive the same
generic `401 Unauthorized` response. The OpenAI provider credential, if
configured, is a separate `AI_PROVIDER_API_KEY` and is never used for API
access.

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
arbitrary provider fields are not returned. Successful responses also contain
a local `persistence_id` and UTC `created_at` timestamp.

Example:

```powershell
curl.exe -X POST http://127.0.0.1:8000/investigate `
  -H "X-API-Key: local-development-key" `
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
PostgreSQL, TLS termination, or deployment configuration. Authentication is
provided by the single application key only. A production deployment still
needs key rotation, rate limiting, TLS, stronger identity and authorization,
monitoring, and real behavioral history.
The API reads the existing saved assessment only and never modifies
`data/raw/creditcard.csv`.

## `GET /investigations/{investigation_id}`

Returns a previously persisted, validated investigation by its positive
integer `persistence_id`. Missing records return `404`.

## `GET /investigations`

Returns recent persisted investigations in deterministic newest-first order.
Optional `source_row_id` filtering is supported. `limit` defaults to 20 and
is bounded from 1 through 100.

Repeated `POST /investigate` calls create new persistence records. The API
does not implement distributed idempotency.
