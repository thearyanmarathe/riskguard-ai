# RiskGuard AI Observability and Reliability

**IMPLEMENTED:** Passive observability surrounds the existing local application. It
does not calculate risk, change authentication, alter AI guardrails, or change
persistence semantics.

## Logging architecture

`scripts/observability.py` uses Python's standard logging library. Important
events are emitted as one compact JSON object per log record. The default
level is `INFO`; configure it with `RISKGUARD_LOG_LEVEL` using `DEBUG`,
`INFO`, `WARNING`, `ERROR`, or `CRITICAL`.

Events contain only safe operational fields: timestamp, event, request ID,
endpoint, status, duration, provider mode, fallback flag, model name, or a
sanitized exception type. Source rows, request bodies, prompts, feature
vectors, database paths, connection strings, and credentials are excluded.

## Request IDs and timing

FastAPI generates a UUID request ID for every request. A supplied
`X-Request-ID` is reused only when it is a valid UUID; unsafe values are
replaced. The resulting ID is returned in the `X-Request-ID` response header
and attached to structured logs. API keys are never used as request IDs.

Durations use `time.perf_counter()` and are logged as non-negative
`duration_ms` values. Investigation totals, persistence operations, and
optional AI operations are timed without exposing those details in responses.

## Lifecycle events

The service emits events only for operations that actually occur:

- `REQUEST_STARTED`, `REQUEST_COMPLETED`, `REQUEST_FAILED`
- `AUTHENTICATION_FAILED`
- `INVESTIGATION_STARTED`, `INVESTIGATION_COMPLETED`, `INVESTIGATION_FAILED`
- `AI_STARTED`, `AI_COMPLETED`, `AI_FALLBACK`, `AI_FAILED`
- `PERSISTENCE_COMPLETED`, `PERSISTENCE_FAILED`
- `READINESS_FAILED` when readiness checks fail

The API consumes saved ML/risk results; it does not run a model prediction per
request, so no synthetic `MODEL_COMPLETED` event is emitted for API reads.

## Health and readiness

`GET /health` remains public and returns only `{"status":"ok"}`.
`GET /ready` is also public for local health probes. It checks SQLite
connectivity and loads the saved XGBoost artifact. Optional OpenAI availability
does not affect readiness because deterministic fallback is supported.

## Failure behavior

Clients receive generic safe errors without tracebacks, SQL details, paths,
environment values, or provider credentials. Persistence failures emit
`PERSISTENCE_FAILED` with a sanitized error type and return HTTP 500; the
authoritative risk decision is not recalculated or changed. AI failures retain
the existing deterministic fallback policy and emit `AI_FALLBACK` or
`AI_FAILED`.

## Local usage and limitations

```powershell
$env:RISKGUARD_LOG_LEVEL = "INFO"
.\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Logs are intended for local diagnostics and are not a replacement for secure
centralized monitoring. Production still needs log access controls, rotation,
redaction review, alerting, TLS, API-key rotation, rate limiting, and
operational monitoring. No external logging, metrics, tracing, or cloud
service was added.

Related documentation: [architecture](ARCHITECTURE.md), [API](API.md),
[security](SECURITY.md), and [deployment](DEPLOYMENT.md).
