# RiskGuard AI Security — Phase 10

RiskGuard AI is a prototype and not a production financial security system. Phase 10 adds a security boundary for any future AI investigator integration while preserving the deterministic investigator and risk engine.

## Trust and data flow

`Kaggle features → XGBoost → ML probability → behavioral rules → deterministic risk score → verified evidence package → optional OpenAI provider → validated bounded recommendation`

Transaction, user, device, region, notes, and other external values are data, never instructions. The guardrails place validated values in an `UNTRUSTED_DATA` message section. The trusted system instruction says to ignore instruction-like content inside that section.

## Input validation

`scripts/ai_guardrails.py` applies an allowlist of evidence fields, type checks, finite-number checks, risk-level validation, string limits, and bounded output-related fields. Common injection patterns are flagged for audit/testing but are never promoted to trusted instructions. Unexpected fields and oversized values are rejected. `scripts/ai_provider.py` sends only the resulting minimized messages.

## Output validation and fallback

AI output must be an exact object containing `summary`, `risk_factors`, `evidence`, `recommended_action`, and `confidence`. Strings, list sizes, action values, and confidence range are validated. Risk fields are not accepted as AI output controls. Malformed output, provider failure, or validation failure uses a deterministic fallback built only from verified application evidence.

## Score protection and action policy

The deterministic risk score, ML probability, behavioral points, and risk level remain authoritative. The AI cannot overwrite them. Recommendations are limited to `ALLOW`, `MONITOR`, `STEP_UP_VERIFICATION`, `MANUAL_REVIEW`, and `TEMPORARY_RESTRICTION`; no action is executed automatically.

## Secrets and logging

`.env` is ignored by Git and `.env.example` contains a placeholder only. This repository has no active provider/API-key integration. Credentials must come from environment variables if a provider is added; they must never be placed in prompts, responses, dashboard output, or logs. Guardrail logging emits event names such as `ai_validation_failed` and `ai_fallback_used`, not raw transaction data or secrets.

## Tools and limitations

The provider adapter exposes no AI tools, shell execution, arbitrary file access, or unrestricted network operation. It uses one finite-timeout HTTPS request with no retries and a bounded response body. The deterministic investigator remains the safe default. The guardrails are not a substitute for provider isolation, authorization, rate limiting, monitoring, or a production security review.

## SQLite persistence

Phase 15 stores only validated application results in `data/riskguard.db`.
The database contains no raw Kaggle rows, V1–V28 vectors, prompts, API keys,
provider credentials, or filesystem paths. SQLAlchemy ORM operations and
bounded validated identifiers and limits protect the repository boundary from
raw SQL injection. The local database has no authentication or retention
policy; production use requires access controls, retention, and encryption or
backup review.

Phase 18 adds database-level range checks for new SQLite tables and matching
repository validation for legacy tables. SQLite writes use SQLAlchemy ORM
operations, foreign keys, and transaction rollback; API query values are
bounded and never concatenated into SQL. Investigation and audit records are
append-only through the current API, with no update or delete routes. The
database stores no prompts, credentials, raw CSV rows, or V1–V28 vectors.
Automatic retention and production database access controls remain future
work.

## API authentication

Investigation endpoints require `RISKGUARD_API_KEY` in the `X-API-Key`
header. Authentication uses constant-time `hmac.compare_digest`; missing and
incorrect keys return the same generic `401 Unauthorized` response. The
public `/health` endpoint exposes only its health status.

The application API key is separate from `AI_PROVIDER_API_KEY`. Neither key
is written to source, tests, reports, logs, responses, prompts, or SQLite.
Authentication is only access control and cannot influence ML probabilities,
behavioral rules, risk scores, risk levels, or AI explanations.

This simple key is not authentication suitable for all production use. Key
rotation, TLS, distributed rate limiting, stronger identity/authorization, and secure
secret storage remain deployment requirements.

## API hardening

The API accepts a strict, bounded `source_row_id` request only. Pydantic
strict integers reject booleans, floats, strings, nulls, negative values, and
out-of-range IDs; unknown fields and unknown investigation-list query names
are rejected. The 4,096-byte body limit is enforced before application
processing. Investigation operations are protected by a bounded,
process-local fixed-window limiter configured with
`RISKGUARD_RATE_LIMIT_REQUESTS` and `RISKGUARD_RATE_LIMIT_WINDOW_SECONDS`.
It returns generic `429` responses with `Retry-After`; it does not persist
state in SQLite and is not a multi-instance production control.

Responses add `X-Content-Type-Options: nosniff`, `X-Frame-Options: DENY`, and
`Referrer-Policy: no-referrer`. CORS remains disabled because the current API
does not require browser cross-origin access; wildcard CORS is not enabled.
Request IDs accept only canonical UUIDs and replace malformed, oversized, or
control-character values. They are never derived from API keys.

Expected validation, authentication, not-found, rate-limit, and dependency
errors are structured and generic. Unexpected errors return no exception
message, traceback, SQL, path, environment, prompt, feature-vector, raw
transaction, or credential data. Existing structured observability records
safe event metadata and retains request correlation without logging request
bodies or headers.

The API uses SQLAlchemy ORM queries and bounded typed identifiers/limits; it
does not concatenate client input into SQL or expose arbitrary query access.
Readiness remains public and reports only a safe status. Investigation
responses remain schema-allowlisted and contain no V1-V28 vectors, prompts,
credentials, or database details. The deterministic risk values remain
application-owned, while optional AI behavior remains behind the existing
guardrails and fallback path.

## Observability and readiness

Structured logs use safe event names, UUID request IDs, endpoint/status
metadata, bounded durations, provider/fallback flags, and sanitized exception
types. They do not contain API keys, OpenAI keys, authentication headers,
prompts, request bodies, raw transaction records, V1–V28 values, CSV contents,
database connection strings, or filesystem paths. `X-Request-ID` values are
accepted only as canonical UUIDs or replaced with generated UUIDs.

`GET /ready` is public and checks local SQLite connectivity and saved model
availability only. Optional OpenAI availability does not make the service
unready because deterministic fallback remains available. Readiness does not
expose internal dependency details.

Persistence failures are logged with only a safe error type and return a
generic server error; SQL details and paths are not exposed. Log rotation,
centralized access control, alerting, and operational monitoring remain
deployment requirements.
