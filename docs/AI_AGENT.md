# RiskGuard AI Investigator and Agent Boundary

## Status

**IMPLEMENTED:** The application has a deterministic Investigator plus an optional guarded provider path. It is not an autonomous fraud-decision agent.

## Responsibilities

The Investigator receives a saved assessment and produces a human-readable summary, evidence, conservative recommendation, and evidence boundary. The deterministic report uses only supplied application fields and stored rule explanations.

The optional provider receives minimized guarded evidence only. **MOCKED DATA** is used in provider tests; no live provider evaluation is recorded. If no provider key is configured, the provider fails, or output validation fails, deterministic fallback is used.

## Non-overridable values

The following remain authoritative application values:

- ML fraud probability
- behavioral points and triggered rules
- deterministic risk score
- deterministic risk level

AI cannot return or overwrite these values. Its output is advisory, and no recommended action is executed automatically.

## Guardrails

The current boundary includes an evidence allowlist, type and finite-number checks, bounded strings/lists, explicit untrusted-data separation, prompt-injection detection for testing/audit, strict output validation, allowed action values, finite timeout, bounded response body, no retries, and no exposed tools for shell, file, or arbitrary network execution.

See [AI provider](AI_PROVIDER.md), [security](SECURITY.md), and [threat model](THREAT_MODEL.md).

## Limitations and future work

**LIMITATION:** no live AI quality, latency, or success-rate evaluation; provider behavior is only tested with mocks and fallback cases.

**PLANNED / FUTURE:** provider-specific operational review, live evaluation under approved controls, and independent production security review.
