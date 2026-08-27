# RiskGuard AI — Phase 9 Behavioral Signal Analysis

## Scope and provenance

This is a read-only analysis of the existing Phase 3 outputs. It reads `behavioral_risk_assessments.csv`, `sample_enriched_transactions.csv`, `methodology.json`, and `behavioral_report.md`; it does not call the behavioral generator or rule engine and does not create new metadata.

The real Kaggle fields are `Time`, `V1`–`V28`, `Amount`, and `Class`. The fields analyzed here—`user_id`, `device_id`, `region`, `transaction_velocity`, `historical_average_amount`, and `amount_deviation`—are fabricated synthetic demonstration metadata. They do not come from the Kaggle dataset and are not XGBoost inputs.

## Current field generation

- `user_id`: reproducibly assigned as `demo_user_###` from seeded random integers from 1 through 500.
- `device_id`: each synthetic user has a deterministic usual device; 12% of generated assignments are deliberately replaced with a different synthetic device.
- `region`: each synthetic user has a deterministic usual region among North, South, East, West, and Central; 10% of generated assignments are deliberately replaced with a different synthetic region.
- `transaction_velocity`: a seeded Poisson-generated count with lambda 1.8, described as prior transactions in a hypothetical recent window. It is not real customer history.
- `historical_average_amount`: a seeded lognormal user-level synthetic baseline generated independently of `Amount`, `Class`, model predictions, and risk scores. It is not real customer history.
- `amount_deviation`: `Amount / historical_average_amount`, safely handled for near-zero baselines. It is a synthetic demonstration ratio, not a production spending profile.

The Phase 3 subset contains 5,000 saved assessments, uses seed 42, and computes the amount rule threshold from the subset at 1115.63. The generated `amount_deviation` distribution has median 0.450, p90 6.295, p95 12.094, p99 41.567, and maximum 738.999. The fixed threshold of 3.0 triggers 903 rows (18.06%), so it is not triggered by almost every transaction; it remains a demonstration choice.

## Current rule behavior and frequencies

Each rule is an independent boolean condition. Points are added when its condition is true; they do not represent learned production fraud evidence.

| signal | field | points | triggered_count | triggered_percent | explanations_present_when_triggered |
| ---: | ---: | ---: | ---: | ---: | ---: |
| High Transaction Velocity | high_transaction_velocity | 20 | 59 | 1.180000 | True |
| Unusual Device | unusual_device | 20 | 598 | 11.960000 | True |
| Unusual Region | unusual_region | 15 | 460 | 9.200000 | True |
| High Transaction Amount | high_transaction_amount | 20 | 50 | 1.000000 | True |
| High Amount Deviation | high_amount_deviation | 20 | 903 | 18.060000 | True |

The existing rules trigger as follows: velocity is synthetic velocity >= 6; unusual device means the synthetic device differs from the synthetic user's deterministic usual device; unusual region means the synthetic region differs from the synthetic user's deterministic usual region; high amount means real Kaggle `Amount` is at least the subset 99th percentile; and high amount deviation means `amount_deviation` >= 3.0. The high-amount rule directly uses a real Kaggle field; the amount-deviation rule uses that field only in combination with a separate synthetic baseline. Both remain separate from XGBoost features.

## Multiple signals

| number_of_triggered_rules | transactions | percent |
| ---: | ---: | ---: |
| 0 | 3250 | 65.000000 |
| 1 | 1458 | 29.160000 |
| 2 | 264 | 5.280000 |
| 3 | 28 | 0.560000 |

292 transactions (5.84%) trigger two or more rules. 3,250 (65.00%) trigger no rules and 1,458 (29.16%) trigger exactly one. The most common trigger-count group is 0 rule(s). The maximum observed is 3 simultaneous rules, with 60 behavioral points.

## Behavioral points and final risk scores

The existing implementation uses `min(100, 60 × ml_fraud_probability + behavioral_rule_points)`. In these saved outputs, mean behavioral points are 7.820, mean final risk score is 7.895, and the ratio of those means is 99.05%. This ratio is descriptive—not a causal or probability interpretation—and ML scores vary across rows.

| behavioral_rule_points | transactions | mean_risk_score | minimum_risk_score | maximum_risk_score | percent |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0 | 3250 | 0.032972 | 0.000000 | 59.990000 | 65.000000 |
| 15 | 329 | 15.010061 | 15.000000 | 15.800000 | 6.580000 |
| 20 | 1129 | 20.178990 | 20.000000 | 80.000000 | 22.580000 |
| 35 | 112 | 35.541071 | 35.000000 | 95.000000 | 2.240000 |
| 40 | 152 | 40.016447 | 40.000000 | 40.340000 | 3.040000 |
| 55 | 19 | 55.020000 | 55.000000 | 55.120000 | 0.380000 |
| 60 | 9 | 60.002222 | 60.000000 | 60.010000 | 0.180000 |

Risk levels by behavioral points alone, while retaining the existing ML contribution, are:

| behavioral_rule_points | LOW | MEDIUM | HIGH |
| ---: | ---: | ---: | ---: |
| 0 | 3249 | 0 | 1 |
| 15 | 329 | 0 | 0 |
| 20 | 1126 | 0 | 3 |
| 35 | 0 | 111 | 1 |
| 40 | 0 | 152 | 0 |
| 55 | 0 | 0 | 19 |
| 60 | 0 | 0 | 9 |

## Representative existing examples

| example | source_row_id | ml_fraud_probability | behavioral_rule_points | risk_score | risk_level | triggered_rules |
| ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| No behavioral signals | 88 | 0.000001 | 0 | 0.000000 | LOW | None |
| One behavioral signal | 26 | 0.000003 | 20 | 20.000000 | LOW | Unusual Device |
| Multiple behavioral signals | 511 | 0.000050 | 35 | 35.000000 | MEDIUM | Unusual Device; Unusual Region |

These are existing saved assessment rows, not newly constructed transactions. The examples show that no rules add zero points, one rule adds its configured 15 or 20 points, and multiple rules add their configured points before the existing cap and level mapping. The new amount-deviation rule contributes 20 points when its demonstration threshold is met.

## Rule review

No current rule is mathematically redundant: the five trigger flags represent different conditions and have distinct behavioral or amount inputs. Three conceptual overlaps are worth documenting:

- Unusual device is a synthetic comparison against a deterministic expected device. It is useful for showing explainable device mismatch, but it is not evidence of real account takeover because there is no real device history.
- Unusual region has the same limitation for location. It is useful as a demonstration of deviation from a synthetic baseline, but it does not establish suspicious geography.
- High amount deviation uses a synthetic user baseline and is distinct from the global high-amount threshold, but both include `Amount`; their overlap should be explained rather than treated as independent evidence.

The high-amount rule is potentially problematic if read as behavioral evidence: it uses real `Amount` and a subset-derived percentile, not transaction history. It is transparent and useful for demonstrating a threshold, but it should not be described as learned fraud behavior. Velocity is also a hypothetical count, not observed history. These are demonstration limitations, not changes to the implementation.

## Candidate richer signals

| Candidate | What it could represent | Data required | Reproducible from current setup? | Demonstration value and risk |
| --- | --- | --- | --- | --- |
| `account_age` | Elapsed time since a synthetic account was opened | Synthetic account creation timestamp and an as-of transaction time | Partly; a seeded synthetic creation date could be generated, but none exists now | Useful for showing account-tenure context. High risk of implying real customer lifecycle data unless explicitly labelled synthetic. |
| `historical_average_amount` | Typical prior transaction amount for a synthetic user | Ordered transaction history and prior amounts per user | Partly; current repeated synthetic users and `Amount` could support a deterministic in-memory history, but that history is not currently stored | Useful baseline for amount context. Must exclude the current transaction and be labelled fabricated history. |
| `amount_deviation` | Difference or ratio between current amount and prior synthetic average | `historical_average_amount`, prior-count rules, and a zero-history policy | Partly; depends on the same synthetic history as above | Likely the most useful companion to historical average because it explains why an amount is unusual for a synthetic user. Can mislead if presented as production spending behavior. |
| `transaction_frequency` | Number or rate of prior transactions in a defined time window | Ordered event times and user history; a clear window definition | Partly; current `Time` is elapsed time and synthetic users repeat, but no real history exists | Potentially useful, but it overlaps strongly with current `transaction_velocity`; adding both could duplicate one concept. |
| `new_device` | Whether a device is first-seen for a synthetic user | Ordered device history by user and a first-seen definition | Partly; current synthetic rows can be ordered by source row, but first-seen history is not an existing field | Useful and more history-oriented than a static mismatch. It can be misleading if the fabricated first-seen sequence is treated as real device telemetry. |
| `location_deviation` | Distance or mismatch from a user's prior synthetic location pattern | Ordered locations plus a baseline or coordinates; current regions are only categorical | Weakly; categorical mismatch is already represented by `unusual_region`; no coordinates or history exist | Low incremental value without richer synthetic geography. Could create false precision or duplicate the existing region rule. |

The most useful candidates for an explicitly labelled demonstration are `historical_average_amount` plus `amount_deviation`, followed by either `new_device` or `transaction_frequency`—but only after defining synthetic history and avoiding duplicate point meanings. The first two are now implemented by the Phase 9 update; the latter candidates remain unimplemented.

Signals I recommend not adding in the next small change are `location_deviation` without coordinates/history, because it would likely duplicate `unusual_region`, and `transaction_frequency` alongside `transaction_velocity` without a distinct time-window definition, because it could be a relabelled duplicate. `account_age` should also wait unless the demonstration needs lifecycle context; it introduces a new synthetic premise with limited connection to the current transaction data.

## Limitations and safeguards

- All six behavioral fields are synthetic demonstration metadata.
- The rule weights and thresholds are demonstration choices, not learned from production fraud outcomes.
- Behavioral association in these outputs does not prove fraud or causation.
- `Amount` is a real Kaggle field, but the high-amount threshold is derived from this demonstration subset.
- Production deployment would require real behavioral history, validated definitions, monitoring, and separate model/rule validation.
- This Phase 9 analysis did not modify existing behavior and did not modify `data/raw/creditcard.csv`.
