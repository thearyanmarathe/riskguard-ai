# RiskGuard AI — Phase 7 Risk Engine Validation

## Scope

This validation reads the existing Phase 3 assessment output and imports the existing `add_risk_assessment` implementation only for mathematical boundary/capping tests. It does not change the risk formula, weights, thresholds, XGBoost model, behavioral generation, investigator, dashboard, or raw dataset.

All 5,000 saved assessments satisfy the existing formula and level mapping:

```text
risk_score = min(100, 60 × ml_fraud_probability + behavioral rule points)
LOW: score < 25; MEDIUM: 25 <= score < 50; HIGH: score >= 50
```

## Representative saved-transaction scenarios

These rows are existing Phase 3 assessment data. They report values only; no reason for an ML output or transaction label is inferred.

| scenario | source_row_id | ml_fraud_probability | behavioral_rule_points | ml_risk_points | risk_score | risk_level | triggered_rules | rule_details | high_transaction_velocity | unusual_device | unusual_region | high_transaction_amount |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Normal transaction (no behavioral rules) | 266961 | 0.000000 | 0 | 0.000000 | 0.000000 | LOW | None | High Transaction Velocity: triggered=False; points=0; explanation=Synthetic velocity is below the demo threshold. \| Unusual Device: triggered=False; points=0; explanation=Synthetic device matches this demo user's usual device. \| Unusual Region: triggered=False; points=0; explanation=Synthetic region matches this demo user's usual region. \| High Transaction Amount: triggered=False; points=0; explanation=Real Kaggle Amount is below the subset 99th-percentile threshold (1115.63). | False | False | False | False |
| High ML probability with no behavioral rules | 43428 | 0.999959 | 0 | 59.997540 | 60.000000 | HIGH | None | High Transaction Velocity: triggered=False; points=0; explanation=Synthetic velocity is below the demo threshold. \| Unusual Device: triggered=False; points=0; explanation=Synthetic device matches this demo user's usual device. \| Unusual Region: triggered=False; points=0; explanation=Synthetic region matches this demo user's usual region. \| High Transaction Amount: triggered=False; points=0; explanation=Real Kaggle Amount is below the subset 99th-percentile threshold (1115.63). | False | False | False | False |
| Low ML probability with one behavioral rule | 116065 | 0.000000 | 15 | 0.000001 | 15.000000 | LOW | Unusual Region | High Transaction Velocity: triggered=False; points=0; explanation=Synthetic velocity is below the demo threshold. \| Unusual Device: triggered=False; points=0; explanation=Synthetic device matches this demo user's usual device. \| Unusual Region: triggered=True; points=15; explanation=Synthetic region differs from this demo user's usual region. \| High Transaction Amount: triggered=False; points=0; explanation=Real Kaggle Amount is below the subset 99th-percentile threshold (1115.63). | False | False | True | False |
| High Transaction Velocity alone | 23637 | 0.000000 | 20 | 0.000002 | 20.000000 | LOW | High Transaction Velocity | High Transaction Velocity: triggered=True; points=20; explanation=Synthetic velocity is at least 6 transactions in the demo window. \| Unusual Device: triggered=False; points=0; explanation=Synthetic device matches this demo user's usual device. \| Unusual Region: triggered=False; points=0; explanation=Synthetic region matches this demo user's usual region. \| High Transaction Amount: triggered=False; points=0; explanation=Real Kaggle Amount is below the subset 99th-percentile threshold (1115.63). | True | False | False | False |
| Unusual Device alone | 191481 | 0.000000 | 20 | 0.000001 | 20.000000 | LOW | Unusual Device | High Transaction Velocity: triggered=False; points=0; explanation=Synthetic velocity is below the demo threshold. \| Unusual Device: triggered=True; points=20; explanation=Synthetic device differs from this demo user's usual device. \| Unusual Region: triggered=False; points=0; explanation=Synthetic region matches this demo user's usual region. \| High Transaction Amount: triggered=False; points=0; explanation=Real Kaggle Amount is below the subset 99th-percentile threshold (1115.63). | False | True | False | False |
| Unusual Region alone | 116065 | 0.000000 | 15 | 0.000001 | 15.000000 | LOW | Unusual Region | High Transaction Velocity: triggered=False; points=0; explanation=Synthetic velocity is below the demo threshold. \| Unusual Device: triggered=False; points=0; explanation=Synthetic device matches this demo user's usual device. \| Unusual Region: triggered=True; points=15; explanation=Synthetic region differs from this demo user's usual region. \| High Transaction Amount: triggered=False; points=0; explanation=Real Kaggle Amount is below the subset 99th-percentile threshold (1115.63). | False | False | True | False |
| High Transaction Amount alone | 17828 | 0.000000 | 20 | 0.000025 | 20.000000 | LOW | High Transaction Amount | High Transaction Velocity: triggered=False; points=0; explanation=Synthetic velocity is below the demo threshold. \| Unusual Device: triggered=False; points=0; explanation=Synthetic device matches this demo user's usual device. \| Unusual Region: triggered=False; points=0; explanation=Synthetic region matches this demo user's usual region. \| High Transaction Amount: triggered=True; points=20; explanation=Real Kaggle Amount is at or above the subset 99th-percentile threshold (1115.63). | False | False | False | True |
| Multiple behavioral signals | 58313 | 0.000000 | 40 | 0.000001 | 40.000000 | MEDIUM | High Transaction Velocity; Unusual Device | High Transaction Velocity: triggered=True; points=20; explanation=Synthetic velocity is at least 6 transactions in the demo window. \| Unusual Device: triggered=True; points=20; explanation=Synthetic device differs from this demo user's usual device. \| Unusual Region: triggered=False; points=0; explanation=Synthetic region matches this demo user's usual region. \| High Transaction Amount: triggered=False; points=0; explanation=Real Kaggle Amount is below the subset 99th-percentile threshold (1115.63). | True | True | False | False |
| High ML probability plus behavioral signals | 215984 | 0.999988 | 15 | 59.999250 | 75.000000 | HIGH | Unusual Region | High Transaction Velocity: triggered=False; points=0; explanation=Synthetic velocity is below the demo threshold. \| Unusual Device: triggered=False; points=0; explanation=Synthetic device matches this demo user's usual device. \| Unusual Region: triggered=True; points=15; explanation=Synthetic region differs from this demo user's usual region. \| High Transaction Amount: triggered=False; points=0; explanation=Real Kaggle Amount is below the subset 99th-percentile threshold (1115.63). | False | False | True | False |

## Boundary and score-capping tests

These are **in-memory mathematical validation cases, not real transactions and not generated behavioral metadata**. They call the existing risk-engine implementation directly.

| scenario | ml_fraud_probability | behavioral_rule_points | ml_risk_points | risk_score | risk_level | expected_score | score_matches_formula | level_matches_boundary | rule_details |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Boundary: 24.99 | 0.416500 | 0 | 24.990000 | 24.990000 | LOW | 24.990000 | True | True | High Transaction Velocity: triggered=False; points=0; explanation=Mathematical test input; no transaction explanation applies. \| Unusual Device: triggered=False; points=0; explanation=Mathematical test input; no transaction explanation applies. \| Unusual Region: triggered=False; points=0; explanation=Mathematical test input; no transaction explanation applies. \| High Transaction Amount: triggered=False; points=0; explanation=Mathematical test input; no transaction explanation applies. |
| Boundary: 25.00 | 0.416667 | 0 | 25.000000 | 25.000000 | MEDIUM | 25.000000 | True | True | High Transaction Velocity: triggered=False; points=0; explanation=Mathematical test input; no transaction explanation applies. \| Unusual Device: triggered=False; points=0; explanation=Mathematical test input; no transaction explanation applies. \| Unusual Region: triggered=False; points=0; explanation=Mathematical test input; no transaction explanation applies. \| High Transaction Amount: triggered=False; points=0; explanation=Mathematical test input; no transaction explanation applies. |
| Boundary: 49.99 | 0.833167 | 0 | 49.990000 | 49.990000 | MEDIUM | 49.990000 | True | True | High Transaction Velocity: triggered=False; points=0; explanation=Mathematical test input; no transaction explanation applies. \| Unusual Device: triggered=False; points=0; explanation=Mathematical test input; no transaction explanation applies. \| Unusual Region: triggered=False; points=0; explanation=Mathematical test input; no transaction explanation applies. \| High Transaction Amount: triggered=False; points=0; explanation=Mathematical test input; no transaction explanation applies. |
| Boundary: 50.00 | 0.833333 | 0 | 50.000000 | 50.000000 | HIGH | 50.000000 | True | True | High Transaction Velocity: triggered=False; points=0; explanation=Mathematical test input; no transaction explanation applies. \| Unusual Device: triggered=False; points=0; explanation=Mathematical test input; no transaction explanation applies. \| Unusual Region: triggered=False; points=0; explanation=Mathematical test input; no transaction explanation applies. \| High Transaction Amount: triggered=False; points=0; explanation=Mathematical test input; no transaction explanation applies. |
| Maximum/capping: raw score 135 | 1.000000 | 75 | 60.000000 | 100.000000 | HIGH | 100.000000 | True | True | High Transaction Velocity: triggered=True; points=20; explanation=Mathematical test input; no transaction explanation applies. \| Unusual Device: triggered=True; points=20; explanation=Mathematical test input; no transaction explanation applies. \| Unusual Region: triggered=True; points=15; explanation=Mathematical test input; no transaction explanation applies. \| High Transaction Amount: triggered=True; points=20; explanation=Mathematical test input; no transaction explanation applies. |

The capping case has ML contribution 60 and all current behavioral rules (75 points), giving an uncapped total of 135. The implementation returns 100, confirming that scores cannot exceed 100.

## Independent rule contribution checks

Each "alone" saved-transaction scenario above has exactly one triggered rule. The observed behavioral points are therefore exactly the configured contribution: velocity 20, unusual device 20, unusual region 15, and high amount 20. Multi-rule scenarios show that contributions add before the score cap is applied.

| rule | points | triggered_transactions | all_triggered_rows_have_explanation |
| ---: | ---: | ---: | ---: |
| High Transaction Velocity | 20 | 59 | True |
| Unusual Device | 20 | 598 | True |
| Unusual Region | 15 | 460 | True |
| High Transaction Amount | 20 | 50 | True |

Every triggered saved rule has a non-empty stored explanation. Existing outputs also retain `triggered_rules`, rule booleans, and the configured point values, making the rule contribution auditable. `user_id`, `device_id`, `region`, and `transaction_velocity` remain explicitly synthetic demonstration metadata; they are not claimed to be Kaggle customer data.

The literal no-rule marker is `None` in the saved CSV. CSV parsing can expose that literal as a null value, so this validator normalizes null/no-rule display to `None` before comparing it with the rule flags. The normalized values are consistent for all saved rows; this is an artifact-format consideration, not a risk-engine scoring inconsistency.

## ML and behavioral-signal disagreement

- **High ML, little/no behavioral contribution:** source row 43428 has ML probability 0.999959, no triggered behavioral rules, score 60.00, and level HIGH. The current system reflects the ML contribution alone.
- **Low ML, behavioral signals raise level:** source row 58313 has ML probability 0.000000, 40 behavioral points from High Transaction Velocity; Unusual Device, score 40.00, and level MEDIUM. The current system adds the explicit rule points to the small ML contribution.
- **High ML plus behavioral signals:** source row 215984 has ML probability 0.999988, 15 behavioral points from Unusual Region, score 75.00, and level HIGH.

These examples show how the configured formula combines signals; they do not establish that either signal is objectively correct.

## Limitations

- Behavioral metadata is synthetic demonstration data.
- Rule weights are demonstration choices, not learned from production fraud outcomes.
- The risk score is not a calibrated probability of fraud.
- The formula is not production-validated, and ML and behavioral signals may disagree.
- Production deployment would require real behavioral history, operational policy, and validation.
