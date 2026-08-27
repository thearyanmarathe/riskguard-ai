# RiskGuard AI — Phase 6 Model Validation

## Scope and reproducibility

This analysis loads `reports/model/xgboost_baseline.json` without fitting, retraining, or tuning it. It recreates the Phase 2 data preparation: exact duplicates are removed only from the in-memory dataframe, then an 80/20 stratified split is made with random seed 42. The raw CSV at `data/raw/creditcard.csv` is read only.

The reconstructed test set contains 56,746 transactions: 56,651 legitimate and 95 fraudulent.

## Reproduced baseline metrics

| metric | phase_2_report | reproduced | difference |
| ---: | ---: | ---: | ---: |
| Precision | 0.914634 | 0.914634 | 0.000000 |
| Recall | 0.789474 | 0.789474 | 0.000000 |
| F1-score | 0.847458 | 0.847458 | 0.000000 |
| Average Precision | 0.821925 | 0.821925 | 0.000000 |

All reproduced values match the saved Phase 2 report to the displayed precision.

### Baseline confusion matrix (model default predictions)

| Actual / predicted | Legitimate (0) | Fraudulent (1) |
| --- | ---: | ---: |
| Legitimate (0) | 56,644 TN | 7 FP |
| Fraudulent (1) | 20 FN | 75 TP |

## False positives

There are 7 false positives: legitimate test transactions predicted as fraudulent at the model's default prediction threshold. The table reports only available transaction fields and model output; it does not infer why these transactions are legitimate.

| source_row_id | Time | Amount | predicted_probability | predicted_class | actual_class |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 120085 | 75706.000000 | 109.900000 | 0.999954 | 1 | 0 |
| 274771 | 166198.000000 | 25691.160000 | 0.876793 | 1 | 0 |
| 59637 | 48930.000000 | 911.090000 | 0.854234 | 1 | 0 |
| 43281 | 41444.000000 | 1.000000 | 0.815574 | 1 | 0 |
| 114902 | 73667.000000 | 8.990000 | 0.810256 | 1 | 0 |
| 274838 | 166235.000000 | 0.000000 | 0.779304 | 1 | 0 |
| 114612 | 73548.000000 | 963.450000 | 0.560076 | 1 | 0 |

## False negatives

There are 20 false negatives: fraudulent test transactions predicted as legitimate at the model's default prediction threshold. The table reports only available transaction fields and model output; it does not infer why the model missed them.

| source_row_id | Time | Amount | predicted_probability | predicted_class | actual_class |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 14338 | 25426.000000 | 3.760000 | 0.439568 | 0 | 1 |
| 229730 | 146026.000000 | 2.220000 | 0.346214 | 0 | 1 |
| 145800 | 87202.000000 | 451.270000 | 0.124944 | 0 | 1 |
| 240222 | 150494.000000 | 1.000000 | 0.055172 | 0 | 1 |
| 195383 | 131024.000000 | 723.210000 | 0.028133 | 0 | 1 |
| 68067 | 52814.000000 | 519.900000 | 0.025229 | 0 | 1 |
| 231978 | 146998.000000 | 8.000000 | 0.009106 | 0 | 1 |
| 68320 | 52934.000000 | 0.760000 | 0.006003 | 0 | 1 |
| 58761 | 48533.000000 | 1.000000 | 0.000924 | 0 | 1 |
| 108258 | 70828.000000 | 0.760000 | 0.000584 | 0 | 1 |
| 154286 | 101051.000000 | 0.920000 | 0.000471 | 0 | 1 |
| 101509 | 67857.000000 | 320.000000 | 0.000306 | 0 | 1 |
| 52521 | 45501.000000 | 105.990000 | 0.000239 | 0 | 1 |
| 274382 | 165981.000000 | 0.000000 | 0.000211 | 0 | 1 |
| 56703 | 47545.000000 | 0.760000 | 0.000147 | 0 | 1 |
| 100623 | 67571.000000 | 549.060000 | 0.000145 | 0 | 1 |
| 249239 | 154309.000000 | 1096.990000 | 0.000087 | 0 | 1 |
| 131272 | 79540.000000 | 0.200000 | 0.000040 | 0 | 1 |
| 72757 | 54846.000000 | 1.790000 | 0.000035 | 0 | 1 |
| 68633 | 53076.000000 | 1.180000 | 0.000023 | 0 | 1 |

## Threshold analysis

| threshold | precision | recall | f1_score | true_negatives | false_positives | false_negatives | true_positives |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 0.100000 | 0.661017 | 0.821053 | 0.732394 | 56611 | 40 | 17 | 78 |
| 0.200000 | 0.740385 | 0.810526 | 0.773869 | 56624 | 27 | 18 | 77 |
| 0.300000 | 0.836957 | 0.810526 | 0.823529 | 56636 | 15 | 18 | 77 |
| 0.400000 | 0.873563 | 0.800000 | 0.835165 | 56640 | 11 | 19 | 76 |
| 0.500000 | 0.914634 | 0.789474 | 0.847458 | 56644 | 7 | 20 | 75 |
| 0.600000 | 0.925926 | 0.789474 | 0.852273 | 56645 | 6 | 20 | 75 |
| 0.700000 | 0.925000 | 0.778947 | 0.845714 | 56645 | 6 | 21 | 74 |
| 0.800000 | 0.935897 | 0.768421 | 0.843931 | 56646 | 5 | 22 | 73 |
| 0.900000 | 0.986301 | 0.757895 | 0.857143 | 56650 | 1 | 23 | 72 |

`threshold_precision_recall.png` shows the same test-set precision/recall trade-off. The 0.50 row reproduces the default prediction operating point: precision 0.914634, recall 0.789474, and F1 0.847458.

## Operating-threshold discussion

Threshold choice is a policy decision, not a model change. Lower thresholds in the table can increase recall (catching more fraud) but increase false positives and therefore manual-investigation workload. Higher thresholds can reduce false positives but miss more fraud. A possible investigation-workflow candidate is 0.40: compared with 0.50, it captures 1 additional fraudulent test transaction(s) (76 versus 75) and reduces false negatives by 1, while adding 4 false-positive reviews (11 versus 7). Whether that workload is acceptable depends on an explicitly defined review capacity and cost of missed fraud. This is an analysis recommendation, not a production decision.

## Class imbalance and limitations

Accuracy is not the primary metric: 56,651 of 56,746 test transactions (99.833%) are legitimate, so an all-legitimate classifier would appear highly accurate while detecting no fraud. Precision, recall, F1, and Average Precision better expose performance on the rare fraud class.

The experiment shows that false positives (7) and false negatives (20) remain, and that threshold changes trade precision for recall. `V1`–`V28` are anonymized/transformed fields, limiting business interpretation of individual model decisions. This is a fixed baseline experiment, not a production fraud system.
