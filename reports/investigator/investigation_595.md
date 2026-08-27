# RiskGuard AI — Phase 4 Investigation Reports

## Investigation: Source Row 595

| Field | Value |
| --- | --- |
| Risk level | LOW |
| Risk score | 20.01 |
| ML fraud probability | 0.000115 |
| Time | 446.00 |
| Amount | 64.00 |

### Key risk signals

- Saved Phase 2 XGBoost baseline fraud probability: 0.000115.
- Transparent risk score: 20.01 (LOW).
- Behavioral-rule points: 20.
- Triggered behavioral rules: High amount deviation.

### Triggered behavioral rules and evidence

- **High amount deviation** (20 points): Synthetic amount is at least 3.0 times the synthetic historical average.

### Synthetic demo context

- User: `demo_user_359`; device: `demo_device_159`; region: `West`; velocity: 1; historical average amount: 17.0079154766171; amount deviation: 3.762953789839136.
- These fields are synthetic demo metadata, not Kaggle customer data.

### Investigation summary

Source row 595 has a LOW transparent risk assessment with score 20.01. The saved XGBoost baseline output is 0.000115, and triggered behavioral rules contribute 20 points. This identifies signals for review; it does not prove fraud.

### Recommended action

No immediate escalation recommended.

### Evidence boundary

This deterministic report uses only supplied assessment fields and stored rule explanations. It does not infer customer history, location, motive, account compromise, or proof of fraud.
