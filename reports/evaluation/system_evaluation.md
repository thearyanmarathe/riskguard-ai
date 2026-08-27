# RiskGuard AI System Evaluation

## Executive Summary

This evaluation measures the existing saved baseline and application outputs.
It performs no retraining, tuning, threshold change, rule change, database
schema change, AI-provider call, or application-logic change. The system has a
measured ML baseline, deterministic risk ownership, bounded API/security
controls, persistence/audit coverage, and reproducible representative results.
It is not a production-validated fraud system.

## Evaluation Scope

Layers evaluated: ML model, class imbalance, threshold behavior, behavioral
engine, deterministic risk engine, Investigator, AI guardrails/fallback, API,
SQLite persistence/audit, dashboard, security, and E2E integration.

## Dataset

The ML evaluation uses the saved Phase 2 metrics and threshold artifact for the
deduplicated 80/20 stratified split (seed 42). The test set contains 56,746
rows: 56,651 legitimate and 95 fraud (0.1674%).
Behavioral evaluation uses 5,000 saved assessments. Behavioral
history, device/region context, historical average amount, and amount deviation
are synthetic demonstration metadata; they are not Kaggle fields.

## ML Model Evaluation

| Metric | Result | Source |
| --- | --- | --- |
| Precision | 0.914634 | reports/model/metrics.json |
| Recall | 0.789474 | reports/model/metrics.json |
| F1 | 0.847458 | reports/model/metrics.json |
| Average Precision / PR-AUC | 0.821925 | reports/model/metrics.json |
| TN / FP / FN / TP | 56644 / 7 / 20 / 75 | reports/model/metrics.json |
| Positive prediction rate | 0.1445% | derived from saved confusion matrix |
| False-positive rate | 0.0124% | derived from saved confusion matrix |
| False-negative rate | 21.0526% | derived from saved confusion matrix |

Accuracy is secondary in this imbalanced setting and is not used as the
primary quality claim. V1–V28 are anonymized/transformed features, so these
metrics do not establish causal feature meanings.

## Class Imbalance

Legitimate: 56,651; fraud: 95; fraud prevalence: 0.1674%.
Accuracy can appear high when the rare fraud class is ignored; precision,
recall, F1, and Average Precision are more informative here.

## Threshold Analysis

Current operating threshold: 0.50, precision 0.914634, recall
0.789474, F1 0.847458. The strongest observed F1
in the saved table is threshold 0.90, F1 0.857143,
precision 0.986301, recall 0.757895.

| Threshold | Precision | Recall | F1 | TP | FP | TN | FN |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 0.10 | 0.661017 | 0.821053 | 0.732394 | 78 | 40 | 56611 | 17 |
| 0.20 | 0.740385 | 0.810526 | 0.773869 | 77 | 27 | 56624 | 18 |
| 0.30 | 0.836957 | 0.810526 | 0.823529 | 77 | 15 | 56636 | 18 |
| 0.40 | 0.873563 | 0.800000 | 0.835165 | 76 | 11 | 56640 | 19 |
| 0.50 | 0.914634 | 0.789474 | 0.847458 | 75 | 7 | 56644 | 20 |
| 0.60 | 0.925926 | 0.789474 | 0.852273 | 75 | 6 | 56645 | 20 |
| 0.70 | 0.925000 | 0.778947 | 0.845714 | 74 | 6 | 56645 | 21 |
| 0.80 | 0.935897 | 0.768421 | 0.843931 | 73 | 5 | 56646 | 22 |
| 0.90 | 0.986301 | 0.757895 | 0.857143 | 72 | 1 | 56650 | 23 |

Lower thresholds generally catch more fraud while creating more false-positive
reviews; higher thresholds generally reduce false positives while potentially
missing more fraud. Threshold selection is a business and operational decision.
The current threshold was not changed.

## Precision-Recall Analysis

Saved Average Precision / PR-AUC is 0.821925. The threshold
table shows the observed precision-recall tradeoff. No new predictions or PR
curve were generated.

## Behavioral Evaluation

5,000 saved assessments were evaluated. No rule triggered in
3,250 (65.00%); exactly
one rule triggered in 1,458; two rules in
264; the maximum was 3
simultaneous rules. Maximum behavioral points were 60.

| Rule | Points | Count | Percentage |
| --- | --- | --- | --- |
| high_transaction_velocity | 20 | 59 | 1.18% |
| unusual_device | 20 | 598 | 11.96% |
| unusual_region | 15 | 460 | 9.20% |
| high_transaction_amount | 20 | 50 | 1.00% |
| high_amount_deviation | 20 | 903 | 18.06% |

## Behavioral Point Distribution

| Behavioral points | Assessments |
| --- | --- |
| 0 | 3250 |
| 15 | 329 |
| 20 | 1129 |
| 35 | 112 |
| 40 | 152 |
| 55 | 19 |
| 60 | 9 |

These are synthetic demonstration rule outputs. Rule frequency is not fraud
effectiveness and does not establish causal or production fraud performance.

## Risk Engine Evaluation

| Level | Count |
| --- | --- |
| LOW | 4704 |
| MEDIUM | 263 |
| HIGH | 33 |

No CRITICAL category is present. Score minimum: 0.00;
maximum: 95.00; average: 7.8952;
median: 0.00. Boundary checks using the
existing implementation returned 24.99 → LOW, 25.00 → MEDIUM, 49.99 → MEDIUM,
and 50.00 → HIGH. The capping case returned raw score 155
→ capped score 100 → HIGH.

## ML + Behavioral Analysis

Average ML probability by level: {'HIGH': 0.15167031406483938, 'LOW': 0.0002663258346794937, 'MEDIUM': 0.00020712670765944867}.
Average behavioral points by level: {'HIGH': 50.90909090909091, 'LOW': 5.836522108843537, 'MEDIUM': 37.88973384030418}.
Observed descriptive examples include 1 high-ML/no-rule
rows, 291 low-ML/non-LOW rows, and
4 high-ML/with-rule rows. These are
descriptive relationships, not causal claims.

## Investigator Evaluation

The deterministic Investigator was run against saved assessments for rows 28727,
233005, and 215984. All preserved the saved risk level, score, ML probability,
and behavioral points, and all used deterministic fallback without a provider.

## AI Investigator Evaluation

No live provider evaluation was performed. Existing mocked tests covered valid
output, malformed/oversized output, invalid actions/confidence, tampering,
prompt injection, secret prevention, and deterministic fallback. Subjective AI
quality, live-provider latency, and provider success rate were not measured.

## API Evaluation

Existing tests cover public health/readiness, protected investigation routes,
strict validation, body size, rate limiting, safe errors, request IDs,
security headers, and persistence integration. No production traffic or latency
benchmark was performed.

## Database Evaluation

Existing tests cover successful persistence, retrieval, deterministic ordering,
constraints, rollback, foreign keys, audit events, and immutable API methods.
SQLite remains a prototype persistence layer; production scalability was not
measured.

## Auditability Evaluation

Creation/completion events, timestamps, deterministic ordering, and bounded safe
metadata were verified. Sensitive prompts, credentials, raw vectors, and raw
CSV rows are not part of persisted audit metadata.

## Dashboard Evaluation

Dashboard helper tests and Streamlit AppTest passed. The console displays stored
results, synthetic metadata labels, fallback status, and audit information
without recalculating risk or writing SQLite. Browser-level testing was not
performed; Streamlit AppTest was used.

## Security Evaluation

Phase 21 focused security tests: 11 in the dedicated file;
the verified Phase 21 full-suite result was 86 passed and 0 failed. No blocking
finding was identified. Security controls passed the implemented test suite;
this is not a claim of absolute security.

## End-to-End Evaluation

The saved E2E result contains 9 passed and 0 failed checks
across saved integrity, risk invariants, Investigator/fallback, mocked AI,
FastAPI, dashboard path, model integrity, reproducibility, and raw hash.

## System Metrics

| Layer | Metric | Result | Source |
| --- | --- | --- | --- |
| ML | F1 | 0.847458 | saved metrics.json |
| ML | PR-AUC | 0.821925 | saved metrics.json |
| Behavioral | Assessments | 5000 | saved assessments CSV |
| Risk | LOW / MEDIUM / HIGH | 4704 / 263 / 33 | saved assessments CSV |
| Security | Focused tests | 11 | test inventory |
| E2E | Passed | 9 | e2e_results.json |
| Tests | Full discovered suite | 86 | test inventory |

## Failure Analysis

- ML: 7 false positives and 20 false negatives remain at the current
  operating threshold; anonymized features limit interpretation.
- Behavioral: context and historical amount are synthetic; frequency does not
  demonstrate fraud effectiveness.
- AI: provider unavailability, malformed output, prompt injection, and output
  tampering use fallback; no live semantic quality evaluation exists.
- API/security: authentication is a single application key and rate limiting is
  process-local.
- Database: SQLite has prototype deployment, backup, retention, and scaling
  limitations.
- Dashboard: no browser-level test was performed.
- Tooling inconsistency: `scripts/validate_risk_engine.py` raises a `KeyError`
  for `high_amount_deviation` in its in-memory capping display because its
  display-name map is stale. This does not alter the risk engine or saved
  assessments and was not changed in this evaluation phase.

## Limitations

The Kaggle dataset is historical and imbalanced; V1–V28 are anonymized. There
is no production behavioral history, live payment integration, live AI provider
evaluation, calibration study, drift monitoring, production load test, TLS or
gateway test, distributed rate limiter, strong identity system, or production
backup/retention evaluation. No throughput, concurrency, provider latency, or
token metrics were measured.

## Overall Assessment

Strengths include a measured ML baseline, deterministic risk ownership,
transparent synthetic behavioral context, explainability artifacts, AI
guardrails and fallback, API security controls, persistence/auditability, and
end-to-end regression coverage. Weaknesses include anonymized data, synthetic
behavioral metadata, limited real-world validation, SQLite, single-key auth,
process-local limiting, no live provider evaluation, and no production
deployment controls. The evidence supports a reproducible prototype
demonstration, not a production-ready fraud system.
