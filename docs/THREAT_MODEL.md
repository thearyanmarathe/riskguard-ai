# RiskGuard AI Threat Model

**IMPLEMENTED:** RiskGuard AI is a prototype fraud-analysis application. The deterministic risk engine remains authoritative; the AI Investigator is an explanation and bounded-recommendation layer.

Related documentation: [architecture](ARCHITECTURE.md), [AI agent boundary](AI_AGENT.md), [security](SECURITY.md), and [AI provider](AI_PROVIDER.md).

## Assets

- Transaction and synthetic context fields
- ML probabilities, behavioral points, and deterministic risk decisions
- AI-bound prompts and responses
- Provider API credentials, if a provider is added later
- Audit and investigation information

## Trust boundaries

Raw transaction/context values are untrusted data. The application validates them before placing them in a clearly marked evidence package. Trusted instructions are kept separate from that package. AI output is validated before application use, and the deterministic risk result is preserved separately.

When configured, the only external boundary is the optional OpenAI Responses API adapter. It receives the minimized guarded message package, never the raw CSV or full dataset. Provider failure returns the deterministic fallback.

## Threats and mitigations

| Threat | Impact | Mitigation |
| --- | --- | --- |
| Prompt injection in transaction metadata | AI manipulation or instruction hijacking | Bounded input validation, instruction-like text detection, explicit `UNTRUSTED_DATA` separation, and trusted system instructions |
| Malicious transaction/context values | Incorrect or misleading explanation | Type, finite-number, field-allowlist, length, and enum validation |
| Malformed or manipulated model output | Incorrect action or unsafe display | Strict response schema, list/string limits, confidence range, allowed-action enum, and deterministic fallback |
| AI score tampering | Authoritative risk decision changed | AI schema excludes risk fields; deterministic score, probability, rule points, and risk level remain application-owned |
| Secret leakage | Credential compromise | `.env` is ignored, no credentials are hard-coded or placed in prompts/logs, and no provider is invoked by this checkout |
| Arbitrary tool execution | Unauthorized file, shell, network, or financial action | No tool-calling framework or tools are exposed; action policy is a fixed enum and recommendations are not executed |
| Oversized input/output | Resource exhaustion or unsafe rendering | Bounded strings, lists, JSON response size, and deterministic rejection/fallback |
| AI/provider unavailable | Missing investigation output | Verified-evidence deterministic fallback |

## Residual risks

This is not a production financial security system. A future provider integration would require authenticated transport, provider-specific controls, redacted telemetry, rate limits, access control, incident response, and independent security review. Detection patterns are not a complete prompt-injection detector.
