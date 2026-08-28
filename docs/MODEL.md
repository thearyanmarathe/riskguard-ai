# RiskGuard AI Model

## Status

**IMPLEMENTED:** The current model is a saved XGBoost baseline evaluated on a held-out, deduplicated, stratified split. This is not a retraining or tuning guide.

## Inputs and provenance

**REAL DATA:** XGBoost uses `Time`, `V1`-`V28`, and `Amount` from the Kaggle `creditcard.csv`. The `V` fields are anonymized/transformed features. `Class` is the fraud label used for evaluation.

**SYNTHETIC DEMO DATA:** `user_id`, `device_id`, `region`, `transaction_velocity`, `historical_average_amount`, and `amount_deviation` are generated demonstration metadata. They are not model inputs and do not represent real customer history.

Exact duplicate removal is performed on an in-memory derived dataframe before the fixed-seed stratified 80/20 split. The raw CSV and saved artifact are not modified by the application.

## Verified evaluation

The checked-in evaluation reports 56,746 held-out rows: 56,651 legitimate and 95 fraud. The saved baseline metrics are:

| Metric | Value |
| --- | ---: |
| Precision | 0.914634 |
| Recall | 0.789474 |
| F1 | 0.847458 |
| Average Precision / PR-AUC | 0.821925 |
| Confusion matrix (TN, FP, FN, TP) | 56644, 7, 20, 75 |

The current operating threshold is `0.50`. A saved threshold table observes F1 `0.857143` at `0.90`, but no threshold change is made or implied here.

## Interpretation boundary

The model produces a probability-like fraud signal; it does not prove fraud, explain a customer’s motive, or provide causal meaning for anonymized features. Model metrics are baseline evidence from this dataset, not production-scale performance, calibration, drift, or fairness validation.

See [model analysis](../reports/model/model_analysis.md), [baseline comparison](../reports/model/baseline_comparison.md), and [explainability methodology](../reports/model/explainability/explainability_methodology.md).

## Limitations and future work

**LIMITATION:** historical imbalanced data, anonymized features, no calibration study, no drift monitoring, and no production load evaluation.

**PLANNED / FUTURE:** independent calibration, drift monitoring, broader validation data, and production governance.
