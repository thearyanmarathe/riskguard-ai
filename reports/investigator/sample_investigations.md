# RiskGuard AI — Phase 4 Investigation Reports

## Investigation: Source Row 114771

| Field | Value |
| --- | --- |
| Risk level | LOW |
| Risk score | 24.07 |
| ML fraud probability | 0.067902 |
| Time | 73615.00 |
| Amount | 162.80 |

### Key risk signals

- Saved Phase 2 XGBoost baseline fraud probability: 0.067902.
- Transparent risk score: 24.07 (LOW).
- Behavioral-rule points: 20.
- Triggered behavioral rules: High amount deviation.

### Triggered behavioral rules and evidence

- **High amount deviation** (20 points): Synthetic amount is at least 3.0 times the synthetic historical average.

### Synthetic demo context

- User: `demo_user_065`; device: `demo_device_065`; region: `Central`; velocity: 1; historical average amount: 14.494960049970173; amount deviation: 11.231490079224814.
- These fields are synthetic demo metadata, not Kaggle customer data.

### Investigation summary

Source row 114771 has a LOW transparent risk assessment with score 24.07. The saved XGBoost baseline output is 0.067902, and triggered behavioral rules contribute 20 points. This identifies signals for review; it does not prove fraud.

### Recommended action

No immediate escalation recommended.

### Evidence boundary

This deterministic report uses only supplied assessment fields and stored rule explanations. It does not infer customer history, location, motive, account compromise, or proof of fraud.

---

## Investigation: Source Row 172250

| Field | Value |
| --- | --- |
| Risk level | MEDIUM |
| Risk score | 40.34 |
| ML fraud probability | 0.005729 |
| Time | 121023.00 |
| Amount | 2500.00 |

### Key risk signals

- Saved Phase 2 XGBoost baseline fraud probability: 0.005729.
- Transparent risk score: 40.34 (MEDIUM).
- Behavioral-rule points: 40.
- Triggered behavioral rules: High transaction amount, High amount deviation.

### Triggered behavioral rules and evidence

- **High transaction amount** (20 points): Real Kaggle Amount is at or above the subset 99th-percentile threshold (1115.63).
- **High amount deviation** (20 points): Synthetic amount is at least 3.0 times the synthetic historical average.

### Synthetic demo context

- User: `demo_user_179`; device: `demo_device_179`; region: `West`; velocity: 3; historical average amount: 48.49459478873989; amount deviation: 51.55213711736143.
- These fields are synthetic demo metadata, not Kaggle customer data.

### Investigation summary

Source row 172250 has a MEDIUM transparent risk assessment with score 40.34. The saved XGBoost baseline output is 0.005729, and triggered behavioral rules contribute 40 points. This identifies signals for review; it does not prove fraud.

### Recommended action

Review the transaction and triggered behavioral signals.

### Evidence boundary

This deterministic report uses only supplied assessment fields and stored rule explanations. It does not infer customer history, location, motive, account compromise, or proof of fraud.

---

## Investigation: Source Row 215984

| Field | Value |
| --- | --- |
| Risk level | HIGH |
| Risk score | 95.00 |
| ML fraud probability | 0.999988 |
| Time | 140308.00 |
| Amount | 592.90 |

### Key risk signals

- Saved Phase 2 XGBoost baseline fraud probability: 0.999988.
- Transparent risk score: 95.00 (HIGH).
- Behavioral-rule points: 35.
- Triggered behavioral rules: Unusual region, High amount deviation.

### Triggered behavioral rules and evidence

- **Unusual region** (15 points): Synthetic region differs from this demo user's usual region.
- **High amount deviation** (20 points): Synthetic amount is at least 3.0 times the synthetic historical average.

### Synthetic demo context

- User: `demo_user_052`; device: `demo_device_052`; region: `East`; velocity: 1; historical average amount: 62.769051944487785; amount deviation: 9.445737694498776.
- These fields are synthetic demo metadata, not Kaggle customer data.

### Investigation summary

Source row 215984 has a HIGH transparent risk assessment with score 95.00. The saved XGBoost baseline output is 0.999988, and triggered behavioral rules contribute 35 points. This identifies signals for review; it does not prove fraud.

### Recommended action

Prioritize this transaction for manual fraud investigation.

### Evidence boundary

This deterministic report uses only supplied assessment fields and stored rule explanations. It does not infer customer history, location, motive, account compromise, or proof of fraud.
