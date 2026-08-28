# RiskGuard AI Deterministic Risk Engine

## Status

**IMPLEMENTED:** Risk scoring is deterministic and application-owned. The engine is not a production-validated financial risk score.

## Inputs and formula

The engine combines the saved ML fraud probability with behavioral rule points:

```text
risk_score = min(100, 60 * ml_fraud_probability + behavioral_points)
```

The current levels are LOW below `25`, MEDIUM from `25` to below `50`, and HIGH at `50` or above. Scores are capped at `100`. The implementation has no CRITICAL level.

Behavioral rules use reproducible context and the real transaction `Amount` where applicable. Context such as device, region, velocity, historical average amount, and amount deviation is **SYNTHETIC DEMO DATA**, not real behavioral history.

## Ownership and evidence

The ML model predicts. The deterministic risk engine decides the score and level. The Investigator explains the stored decision and evidence. Optional AI may return a validated advisory explanation and allowed action, but cannot change `ml_fraud_probability`, `behavioral_points`, `risk_score`, `risk_level`, or triggered rule evidence.

## Verified examples

The saved system evaluation records:

| Source row | Level | Score | ML probability | Behavioral points |
| ---: | --- | ---: | ---: | ---: |
| 28727 | LOW | 20.95 | 0.01587517 | 20 |
| 233005 | MEDIUM | 40.13 | approximately 0.002242215 | 40 |
| 215984 | HIGH | 95.00 | approximately 0.9999875 | 35 |

The 5,000 saved assessments contain 4,704 LOW, 263 MEDIUM, and 33 HIGH results. These are descriptive outputs, not fraud-effectiveness claims.

## Validation and limitations

Saved boundary checks are `24.99 -> LOW`, `25.00 -> MEDIUM`, `49.99 -> MEDIUM`, and `50.00 -> HIGH`; a raw score of `155` is capped at `100` and classified HIGH. See [risk validation](../reports/risk/risk_engine_validation.md) and [system evaluation](../reports/evaluation/system_evaluation.md).

**LIMITATION:** rule frequencies do not establish causal or production fraud performance, and a high score is an investigation signal rather than proof of fraud.

**PLANNED / FUTURE:** calibration and operational validation are separate future work.
