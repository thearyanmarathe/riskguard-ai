# RiskGuard AI Technical Talking Points

## 1. Why XGBoost?

It is the saved baseline used by this project and provides a compact, reproducible model for tabular transaction features. The project evaluates it with imbalance-aware metrics rather than accuracy alone.

## 2. Why not only ML?

The probability ranks model signal but does not provide all the contextual evidence an investigator needs. Behavioral rules add transparent, reviewable signals.

## 3. Why behavioral rules?

They make additional evidence explicit: velocity, device, region, amount, and amount deviation. The behavioral metadata is synthetic demo data, not real customer history.

## 4. Why deterministic risk scoring?

It makes ownership, thresholds, and outcomes inspectable and reproducible. The deterministic engine—not an LLM—owns the score and risk level.

## 5. Why use an LLM?

Only as an optional investigation assistant to summarize supplied evidence and suggest an advisory action. It is not needed for a valid result.

## 6. Why can't the LLM decide risk?

Unrestricted model output is not an appropriate authority for a financial decision. The application preserves ML probability, behavioral points, score, level, and rules as authoritative values.

## 7. How is prompt injection handled?

Inputs are treated as untrusted data, minimized and allowlisted, separated from trusted instructions, and checked for injection-shaped content. Provider output is strictly validated.

## 8. What happens when AI is unavailable?

The deterministic Investigator returns a valid evidence-based report. This is the normal demo path without an AI key.

## 9. Why FastAPI?

It provides a thin, typed HTTP boundary around the existing Investigator and persistence path without moving prediction or risk ownership into the API layer.

## 10. Why Streamlit?

It provides a lightweight local investigation console for presenting saved decisions, evidence, fallback state, and audit history.

## 11. Why SQLite?

It is sufficient for this controlled local prototype and supports persisted investigations and audit events. It is not presented as a production-scale database.

## 12. What data is real?

The Kaggle transaction rows, anonymized `V1`-`V28` features, real `Amount`/`Time` fields, saved ML outputs, and persisted investigations are REAL DATA or real derived application records.

## 13. What data is synthetic?

Behavioral history, historical average amount, amount deviation, device context, region context, and velocity are SYNTHETIC DEMO DATA.

## 14. What are the ML results?

On 56,746 held-out rows: precision 0.914634, recall 0.789474, F1 0.847458, and PR-AUC 0.821925. The confusion matrix is TN 56,644, FP 7, FN 20, TP 75.

## 15. What are the limitations?

The data is historical/anonymized, behavioral context is synthetic, AI has no live evaluation, SQLite and rate limiting are local, and there is no real payment or Razorpay integration.

## 16. What would be needed for production?

Stronger identity and authorization, TLS/gateway controls, distributed rate limiting, managed database operations, monitoring, backup/retention, model monitoring, calibration, controlled provider evaluation, and real behavioral data governance.

## 17. Why is this relevant to payment platforms?

Payment platforms face the general challenge of combining fast risk signals with explainable review. RiskGuard is a prototype relevant to payment-risk investigation and can be framed as a Razorpay-style scenario, without claiming Razorpay integration or data.

## Honest AI positioning

AI is an investigation assistant, not the decision maker. The deterministic system owns the score, risk level, behavioral points, and rules. AI summarizes evidence, identifies risk factors, recommends an advisory action, and fails safely to deterministic fallback.

## Security story

```text
UNTRUSTED DATA -> INPUT VALIDATION -> MINIMIZED EVIDENCE -> AI GUARDRAILS -> STRICT OUTPUT VALIDATION -> ADVISORY RESULT
```

```text
API KEY -> AUTHENTICATION -> REQUEST VALIDATION -> RATE LIMITING -> SAFE RESPONSE
```

## Failure story

- AI unavailable -> deterministic fallback
- Invalid AI output -> rejected/fallback
- Risk tampering -> rejected/fallback
- Invalid API request -> 422 validation response
- Unauthorized request -> 401
- Oversized request -> 413
- Rate limit exceeded -> 429
- Database failure -> safe failure response

These are implemented local behaviors, not claims of automatic recovery.
