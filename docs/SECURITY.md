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
