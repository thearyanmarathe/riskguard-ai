# RiskGuard AI — Phase 3: Synthetic Behavioral Context and Rule Engine

## Data separation

- **Real Kaggle fields:** `Time`, `V1`–`V28`, `Amount`, and `Class`. These are read from `data/raw/creditcard.csv` without modification.
- **Synthetic demo fields:** `user_id`, `device_id`, `region`, `transaction_velocity`, `historical_average_amount`, and `amount_deviation`. They are deterministic fabricated metadata for this classroom/demo layer; they do not come from Kaggle and are not ML model inputs.

## Synthetic methodology

A deterministic random subset of 5,000 Kaggle transactions was selected with seed 42. Synthetic users have a deterministic usual device and usual region; 12% of generated device assignments and 10% of generated region assignments are deliberately different, enabling rule-engine demonstrations. `transaction_velocity` is a synthetic Poisson-generated count in a hypothetical recent window, not real customer behavior. `historical_average_amount` is a seeded, user-level synthetic baseline generated independently of `Amount` and `Class`; it is not real customer history. `amount_deviation = Amount / historical_average_amount`, with safe handling for near-zero baselines. In the generated distribution, the median was 0.450, the 90th percentile 6.295, the 95th percentile 12.094, the 99th percentile 41.567, and the maximum 738.999. The fixed demonstration threshold of 3.0 triggers 903 transactions (18.06%); it was selected after inspecting this distribution and is not learned from production outcomes.

## ML signal status

`available: saved Phase 2 XGBoost baseline scored real Kaggle feature columns only`. `ml_fraud_probability` is the saved Phase 2 XGBoost baseline's probability using only the real Kaggle transaction feature columns (`Time`, `V1`–`V28`, and `Amount`). Synthetic fields are not model inputs and are not claimed to improve the ML baseline.

Across the 5,000 scored transactions, ML probability is minimum 0.000000004592, maximum 0.999987483025, mean 0.001262478298, and median 0.000008363928.

## Rules

| Rule | Trigger condition | Points | Triggered transactions |
| --- | --- | ---: | ---: |
| High transaction velocity | Synthetic velocity >= 6 | 20 | 59 |
| Unusual device | Synthetic device differs from the user's synthetic usual device | 20 | 598 |
| Unusual region | Synthetic region differs from the user's synthetic usual region | 15 | 460 |
| High transaction amount | Real `Amount` >= subset 99th percentile (1115.63) | 20 | 50 |
| High amount deviation | `Amount / historical_average_amount` >= 3.0 | 20 | 903 |

Each rule produces a boolean trigger and a short explanation. The assessment output includes all five trigger and explanation columns, plus the combined triggered-rule names and risk explanation. The amount-deviation rule is a demonstration heuristic, not a production-learned rule.

## Risk assessment

`risk_score = min(100, 60 × ml_fraud_probability + behavioral rule points)`.

Rule points are 20 (velocity), 20 (device), 15 (region), 20 (amount), and 20 (amount deviation). Risk levels are **LOW** below 25, **MEDIUM** from 25 to below 50, and **HIGH** at 50 or greater. This is a transparent demonstration formula, not a production-validated financial risk score.

## Example assessments

| Source row | Amount | ML probability | Rule points | Risk score | Risk level | Triggered rules |
| ---: | ---: | ---: | ---: | ---: | --- | --- |
| 215984 | 592.90 | 0.999987 | 35 | 95.00 | HIGH | Unusual Region; High Amount Deviation |
| 43428 | 364.19 | 0.999959 | 20 | 80.00 | HIGH | High Amount Deviation |
| 116404 | 311.28 | 0.999896 | 20 | 79.99 | HIGH | High Amount Deviation |

## Outputs

- `sample_enriched_transactions.csv` — first 25 enriched transactions.
- `behavioral_risk_assessments.csv` — all 5,000 assessed subset rows with real reference fields and synthetic/demo fields.
- `methodology.json` — fixed seed, field separation, thresholds, and rule counts.
