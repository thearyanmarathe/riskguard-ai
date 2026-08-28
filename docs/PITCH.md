# RiskGuard AI

## One-Line Pitch

An explainable fraud-risk investigation prototype combining ML probability, deterministic behavioral evidence, and a guarded AI Investigator for human review.

## Problem

Payment fraud is difficult to investigate from a single signal. An ML probability can rank risk, but analysts also need interpretable evidence and a clear boundary around what is known. AI can summarize evidence, but it should not control a financial decision.

## Solution

```text
Transaction
    -> ML prediction
    -> Behavioral analysis
    -> Deterministic risk engine
    -> AI investigation / deterministic fallback
    -> Human review
```

The model predicts. Behavioral signals add evidence. The deterministic engine owns the authoritative score and level. The Investigator explains the evidence and provides an advisory recommendation.

## Problem -> Solution -> Impact

**Problem:** Fraud signals are fragmented and analysts need explainable evidence.

**Solution:** ML probability + deterministic behavioral evidence + guarded AI investigation.

**Impact:** A reproducible, more explainable investigation flow while keeping the authoritative decision deterministic and auditable. No business KPI is claimed.

## Why It Is Different

- ML and behavioral evidence are shown together.
- Risk ownership remains deterministic and application-controlled.
- AI is an explanation layer, not an autonomous fraud-prevention system.
- Recommendations stay human-in-the-loop.
- Input/output guardrails defend the optional provider boundary.
- SQLite persistence and append-only audit events support local traceability.
- The three-scenario demo is reproducible from saved assessments.

## Technical Architecture

The XGBoost baseline consumes REAL Kaggle fields (`Time`, `V1`-`V28`, `Amount`). Behavioral context is SYNTHETIC DEMO DATA. The deterministic Investigator consumes saved assessment evidence. Optional AI receives minimized guarded evidence, and strict validation preserves authoritative values. FastAPI exposes authenticated investigation operations; SQLite stores validated results and audit events; Streamlit presents them read-only. Structured observability, request IDs, API-key authentication, safe errors, and process-local rate limiting are implemented local controls.

See [architecture](ARCHITECTURE.md), [model](MODEL.md), [risk engine](RISK_ENGINE.md), and [AI agent boundary](AI_AGENT.md).

## AI Safety

```text
UNTRUSTED DATA
    -> INPUT VALIDATION
    -> MINIMIZED EVIDENCE
    -> AI GUARDRAILS
    -> OPTIONAL AI PROVIDER
    -> STRICT OUTPUT VALIDATION
    -> ADVISORY RESULT
```

The AI cannot change the ML probability, behavioral points, score, risk level, or deterministic rules. When AI is unavailable or unsafe, the deterministic Investigator remains the fallback and source of truth.

## Security

Implemented controls include API-key authentication with constant-time comparison, strict input validation, request-size limits, process-local rate limiting, safe errors, security headers, prompt-injection defenses, secret redaction, and append-only audit events. The security assessment found no blocking defect in the tested local application chain; residual deployment risks remain.

```text
API KEY -> AUTHENTICATION -> REQUEST VALIDATION -> RATE LIMITING -> SAFE RESPONSE
```

See [security](SECURITY.md), [threat model](THREAT_MODEL.md), and [security test report](SECURITY_TEST_REPORT.md).

## Evaluation

The held-out evaluation contains 56,746 rows: 56,651 legitimate and 95 fraud. The saved XGBoost baseline reports precision `0.914634`, recall `0.789474`, F1 `0.847458`, and PR-AUC `0.821925`, with confusion matrix TN `56,644`, FP `7`, FN `20`, TP `75`. Fraud prevalence is approximately `0.1674%`; the current threshold is `0.50`.

These are dataset-level baseline measurements, not production performance claims. The current full test suite has 108 passing tests; the historical Phase 21 security assessment records 86 tests. They must not be conflated.

## Demo

The reproducible scenarios are LOW row `28727`, MEDIUM row `233005`, and HIGH row `215984`. The HIGH story uses score `95.00`, ML probability approximately `0.9999875`, 35 behavioral points, and unusual-region/high-amount-deviation rules. See [DEMO_SCRIPT.md](DEMO_SCRIPT.md) and [DEMO.md](DEMO.md).

## Razorpay positioning

RiskGuard AI is a prototype relevant to payment-risk investigation and can be presented as a Razorpay-style payment-risk scenario. It was not built for Razorpay, does not use Razorpay data, and is not integrated with or endorsed by Razorpay.

## Limitations

- Kaggle data is historical and anonymized.
- Behavioral metadata is synthetic and is not real customer history.
- There is no real payment or Razorpay integration.
- Optional AI has not been live-evaluated.
- SQLite and rate limiting are local/process-scoped.
- There is no production identity, TLS/gateway, centralized monitoring, or high-availability infrastructure.

## Future Work

Production database operations, distributed limiting, stronger identity, production observability, model monitoring, real behavioral history, controlled provider evaluation, and a payment-platform integration would require separate design and validation.

## Claims To Avoid

Do not say the AI detects fraud by itself, the LLM decides risk, the system automatically blocks transactions, behavioral data comes from real customers, the system is production-ready, it is connected to Razorpay, or the AI was evaluated live.
