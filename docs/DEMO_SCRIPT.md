# RiskGuard AI — Five-Minute Demo Script

## 0:00–0:30 — Problem

**Presenter says:** “Fraud detection alone is not enough for an investigator. A model can identify a suspicious probability, but a reviewer also needs interpretable context and a safe explanation.”

**Presenter shows:** The RiskGuard AI dashboard overview.

**Expected screen/output:** The investigation console with persisted overview metrics and LOW/MEDIUM/HIGH distribution.

**Key point:** RiskGuard combines ML prediction, behavioral evidence, deterministic scoring, and investigation context.

## 0:30–1:00 — Architecture

**Presenter says:** “The separation is important: ML predicts, the deterministic risk engine owns the decision, and the AI Investigator explains evidence and offers an advisory recommendation.”

**Presenter shows:** The architecture overview in [ARCHITECTURE.md](ARCHITECTURE.md), then the dashboard’s risk-decision and AI-investigation tabs.

**Expected screen/output:** The flow from saved assessment to deterministic decision, optional guarded AI, fallback, and audit history.

**Key point:** AI cannot override ML probability, behavioral points, risk score, risk level, or deterministic rules.

## 1:00–1:45 — ML evidence

**Presenter says:** “The model uses the real Kaggle transaction fields and produces a fraud probability. These anonymized features are useful for prediction, but they do not by themselves explain customer intent.”

**Presenter shows:** The ML evidence tab for a selected investigation and the saved baseline metrics in [MODEL.md](MODEL.md).

**Expected screen/output:** A stored ML probability and model evidence; no V1–V28 vector dump is needed.

**Key point:** ML output is a signal, not the final business decision.

## 1:45–2:45 — Suspicious transaction

**Presenter says:** “I’ll use the verified HIGH scenario, source row 215984. Its saved ML probability is approximately 0.9999875. The assessment also has 35 behavioral points from unusual region and high amount deviation.”

**Presenter shows:** Search/select source row `215984`, then the Overview, ML evidence, Behavioral evidence, and Risk decision tabs.

**Expected screen/output:** HIGH, risk score `95.00`, ML probability `0.9999875`, behavioral points `35`, and the two triggered rules.

**Presenter adds:** “The transaction row and ML output are REAL DATA. The region, historical amount, and amount deviation are SYNTHETIC DEMO DATA; they are not real customer history.”

**Key point:** Multiple interpretable signals give an investigator more context without changing the authoritative risk engine.

## 2:45–3:40 — AI Investigator

**Presenter says:** “The AI layer is optional. With no provider key, the deterministic Investigator remains the fallback and source of truth. It summarizes only supplied evidence and does not invent history or proof of fraud.”

**Presenter shows:** The AI investigation tab for source row `215984`, including provider/fallback status and recommendation.

**Expected screen/output:** “Deterministic fallback” or equivalent fallback status, an evidence-based summary, and the advisory manual-review recommendation.

**Key point:** MOCKED AI PROVIDER RESPONSE is only used in tests; this demo makes no live OpenAI call.

## 3:40–4:20 — Human review + audit trail

**Presenter says:** “The recommendation is advisory. The system does not automatically block a transaction or execute a financial action. The analyst or organization decides what happens next.”

**Presenter shows:** The Audit history tab for the selected persisted investigation, then the deterministic decision tab.

**Expected screen/output:** Safe creation/completion audit metadata and the unchanged HIGH decision.

**Key point:** HIGH → AI investigation → MANUAL_REVIEW recommendation → human/analyst decision.

## 4:20–5:00 — Limitations + future

**Presenter says:** “This is a reproducible prototype relevant to payment-risk investigation, including a Razorpay-style payment-risk scenario. It is not connected to Razorpay, does not use Razorpay data, and is not production-ready.”

**Presenter shows:** The limitations section of [DEMO.md](DEMO.md) and the readiness matrix in [ARCHITECTURE.md](ARCHITECTURE.md).

**Expected screen/output:** Clear labels for real Kaggle data, synthetic behavioral metadata, mocked provider tests, and future production work.

**Key point:** The prototype demonstrates safe evidence flow; it does not claim real behavioral history, live AI evaluation, browser testing, Docker runtime testing, or automatic fraud blocking.

## Failure fallback plan

- **AI provider unavailable:** Explain the deterministic fallback and continue with the valid investigation result.
- **API unavailable:** Use the read-only dashboard or the local CLI runner.
- **Dashboard unavailable:** Run `scripts/run_demo.py` and show its verified CLI output.
- **Database issue:** Do not reset or modify the database during the demo; stop and report the issue.
- **Unexpected result:** Stop rather than inventing output or changing a threshold/rule.

The demo prioritizes correctness over appearance.
