# RiskGuard AI Security Test Report

## Scope

Phase 21 assessed the current API, authentication, rate limiter, AI guardrail
boundary, provider adapter, persistence/audit path, Streamlit presentation
layer, logging, secrets, filesystem boundaries, and representative risk
integrity. Testing was limited to security assessment and regression testing.
No model, risk rule, AI architecture, database schema, API design, or
dashboard behavior was intentionally changed in this phase.

## Methodology

The repository was reviewed before testing for trust boundaries, authentication
boundaries, provider messages, database access, logging, filesystem inputs,
and arbitrary execution surfaces. Focused standard-library `unittest` cases
then used mocked providers and temporary databases. API failures, malformed
inputs, injection-shaped values, oversized requests, repeated requests, and
unsupported methods were tested through `TestClient`. Streamlit `AppTest` and
source-boundary checks covered presentation leakage. Raw-data and model/risk
integrity were checked before and after regression commands.

## Threat Areas

- Authentication and protected-route bypass
- API input, query, path, content-type, and body-size handling
- AI prompt injection, output tampering, secrets, and fallback
- Database and audit read/write boundaries
- Dashboard presentation leakage
- Secrets and logging
- Filesystem and arbitrary-execution surfaces
- Rate limiting and resource exhaustion

## Results

| Test | Expected | Actual | Result |
| --- | --- | --- | --- |
| Prompt injection in transaction/context values | Values remain untrusted data | Guardrails marked injection-like content and kept it out of trusted instructions | MITIGATED |
| System-prompt extraction and tool requests | No prompt disclosure or tools | No trusted prompt disclosure; no tool surface exposed | PASS |
| AI risk/action/field tampering | Fallback with authoritative risk preserved | Score, level, behavioral points, and ML probability remained application-owned | PASS |
| AI malformed, oversized, invalid-action, and invalid-confidence output | Validation failure and fallback | Strict validation rejected unsafe output; deterministic fallback returned | PASS |
| AI/provider secret leakage | No credentials, prompts, paths, or raw vectors | No secrets or sensitive internals appeared in messages, fallback, or tested responses | PASS |
| Missing, empty, whitespace, incorrect, and long API keys | Generic unauthorized response | Protected endpoints returned generic 401; health/readiness remained public | PASS |
| Authentication bypass paths/methods | Protected resources remain protected | Alternate methods/paths produced safe 307/401/404/405/422 responses | PASS |
| API body fuzzing | Safe 4xx, no crash or leakage | Invalid IDs, booleans, floats, strings, arrays, objects, and fields were rejected | PASS |
| Query/path SQL-injection and traversal inputs | Harmless rejection/lookup | Inputs were rejected or returned safe not-found behavior; ORM remained parameterized | PASS |
| Request body limit | Below-limit success; above-limit 413 | 4,096-byte boundary behaved correctly | PASS |
| Rate limiting | Threshold, 429, Retry-After, bounded local state | Configured isolated test reached 429 with valid Retry-After; health remained available | PASS |
| Request-ID injection | Safe UUID response and no log injection | Valid UUIDs were preserved; malformed/control/script/key-looking values were replaced | PASS |
| Security headers and CORS | Protective headers; no unsafe wildcard CORS | `nosniff`, `DENY`, and `no-referrer` present; no CORS allow-origin header | PASS |
| Unsupported PUT/PATCH/DELETE | No mutation | Methods returned 405 and records remained present | PASS |
| Wrong content type/malformed JSON | Safe validation response | Text/plain and malformed JSON returned 422 | PASS |
| Database failure and missing investigation | Generic safe errors | No database message/path leaked; missing records returned safe 404 | PASS |
| Audit integrity | Read-only, safe metadata | Audit events remained present and metadata was limited to provider/fallback flags | PASS |
| Dashboard leakage and mutation surface | No secrets, raw vectors, prompts, paths, or writes | Source and helper tests found no prohibited display/execution surface | PASS |
| AI fallback | Deterministic usable result without provider key | Fallback remained functional with no external call | PASS |
| Representative risk integrity | Existing authoritative values unchanged | LOW/MEDIUM/HIGH results matched expected values | PASS |

## Findings

### F-001 — Single environment API key

- Severity: Medium residual risk
- Description: Protected API access uses one `RISKGUARD_API_KEY` value.
- Impact: Rotation, identity-level attribution, and granular authorization are
  limited.
- Evidence: Authentication review and regression tests confirmed the current
  constant-time comparison and generic responses.
- Mitigation: Existing constant-time comparison, generic 401 behavior, and
  no-key logging were retained.
- Residual risk: Production use requires stronger identity, authorization,
  rotation, TLS, and secret management.

### F-002 — Process-local rate limiter

- Severity: Low residual risk for this prototype
- Description: Rate-limit state exists only in one process.
- Impact: It does not coordinate limits across multiple instances or workers.
- Evidence: Isolated threshold, Retry-After, expiration, and bounded-state
  tests passed.
- Mitigation: Configurable fixed-window limiter with cleanup and a maximum
  tracked-client bound.
- Residual risk: Distributed deployments require an external coordinated
  control.

### F-003 — Local transport/deployment boundary

- Severity: Medium deployment limitation
- Description: The tested local service does not provide TLS termination or a
  production gateway.
- Impact: Network confidentiality and operational controls depend on the
  deployment environment.
- Evidence: This phase intentionally did not deploy or add infrastructure.
- Mitigation: Local binding and application-level authentication remain in
  place.
- Residual risk: Production deployment requires TLS, gateway controls,
  monitoring, incident response, and independent security review.

## Risk Integrity

| Source row | Level | Risk score | ML probability | Behavioral points |
| ---: | --- | ---: | ---: | ---: |
| 28727 | LOW | 20.95 | 0.01587517 | 20 |
| 233005 | MEDIUM | 40.13 | approximately 0.002242215 | 40 |
| 215984 | HIGH | 95.00 | approximately 0.9999875 | 35 |

These values came from existing saved assessments and Investigator output;
they were not added to application logic.

## Data Integrity

Raw `data/raw/creditcard.csv` SHA-256 before and after testing:

```text
76274B691B16A6C49D3F159C883398E03CCD6D1EE12D9D8EE38F4B4B98551A89
```

The hash was unchanged. Security tests used temporary databases and did not
modify raw data.

## Model Integrity

The existing XGBoost artifact was not retrained, rewritten, or replaced.
Representative probabilities remained consistent. No real OpenAI request was
made; provider behavior was mocked or deterministic fallback was used.

## Limitations

This is a repository-level prototype assessment, not a penetration test or
formal production security review. It does not test TLS, reverse proxies,
multi-instance rate limiting, real identity providers, browser isolation,
dependency vulnerabilities beyond `pip check`, operating-system permissions,
or live provider behavior. Secret scanning can identify likely patterns but
cannot prove that external systems or developer machines contain no secrets.

## Overall assessment

No blocking security defect was found in the tested local application chain.
Existing controls mitigated the tested injection, tampering, leakage,
authentication, input-validation, resource, database, audit, and dashboard
cases. The residual findings are deployment and prototype-architecture
limitations, not changes to the authoritative fraud/risk behavior.
