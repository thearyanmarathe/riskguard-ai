# RiskGuard AI — Phase 4 Investigation Reports

## Investigation: Source Row 28727

| Field | Value |
| --- | --- |
| Risk level | LOW |
| Risk score | 20.95 |
| ML fraud probability | 0.015875 |
| Time | 35129.00 |
| Amount | 1.00 |

### Key risk signals

- Saved Phase 2 XGBoost baseline fraud probability: 0.015875.
- Transparent risk score: 20.95 (LOW).
- Behavioral-rule points: 20.
- Triggered behavioral rules: Unusual device.

### Triggered behavioral rules and evidence

- **Unusual device**: Synthetic device differs from this demo user's usual device.

### Synthetic demo context

- User: `demo_user_138`; device: `demo_device_039`; region: `East`; velocity: 2.
- These fields are synthetic demo metadata, not Kaggle customer data.

### Investigation summary

Source row 28727 has a LOW transparent risk assessment with score 20.95. The saved XGBoost baseline output is 0.015875, and triggered behavioral rules contribute 20 points. This identifies signals for review; it does not prove fraud.

### Recommended action

No immediate escalation recommended.

### Evidence boundary

This deterministic report uses only supplied assessment fields and stored rule explanations. It does not infer customer history, location, motive, account compromise, or proof of fraud.

---

## Investigation: Source Row 233005

| Field | Value |
| --- | --- |
| Risk level | MEDIUM |
| Risk score | 40.13 |
| ML fraud probability | 0.002242 |
| Time | 147404.00 |
| Amount | 2.31 |

### Key risk signals

- Saved Phase 2 XGBoost baseline fraud probability: 0.002242.
- Transparent risk score: 40.13 (MEDIUM).
- Behavioral-rule points: 40.
- Triggered behavioral rules: High transaction velocity, Unusual device.

### Triggered behavioral rules and evidence

- **High transaction velocity**: Synthetic velocity is at least 6 transactions in the demo window.
- **Unusual device**: Synthetic device differs from this demo user's usual device.

### Synthetic demo context

- User: `demo_user_257`; device: `demo_device_130`; region: `South`; velocity: 7.
- These fields are synthetic demo metadata, not Kaggle customer data.

### Investigation summary

Source row 233005 has a MEDIUM transparent risk assessment with score 40.13. The saved XGBoost baseline output is 0.002242, and triggered behavioral rules contribute 40 points. This identifies signals for review; it does not prove fraud.

### Recommended action

Review the transaction and triggered behavioral signals.

### Evidence boundary

This deterministic report uses only supplied assessment fields and stored rule explanations. It does not infer customer history, location, motive, account compromise, or proof of fraud.

---

## Investigation: Source Row 215984

| Field | Value |
| --- | --- |
| Risk level | HIGH |
| Risk score | 75.00 |
| ML fraud probability | 0.999988 |
| Time | 140308.00 |
| Amount | 592.90 |

### Key risk signals

- Saved Phase 2 XGBoost baseline fraud probability: 0.999988.
- Transparent risk score: 75.00 (HIGH).
- Behavioral-rule points: 15.
- Triggered behavioral rules: Unusual region.

### Triggered behavioral rules and evidence

- **Unusual region**: Synthetic region differs from this demo user's usual region.

### Synthetic demo context

- User: `demo_user_052`; device: `demo_device_052`; region: `East`; velocity: 1.
- These fields are synthetic demo metadata, not Kaggle customer data.

### Investigation summary

Source row 215984 has a HIGH transparent risk assessment with score 75.00. The saved XGBoost baseline output is 0.999988, and triggered behavioral rules contribute 15 points. This identifies signals for review; it does not prove fraud.

### Recommended action

Prioritize this transaction for manual fraud investigation.

### Evidence boundary

This deterministic report uses only supplied assessment fields and stored rule explanations. It does not infer customer history, location, motive, account compromise, or proof of fraud.
