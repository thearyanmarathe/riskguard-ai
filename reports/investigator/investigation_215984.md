# RiskGuard AI — Phase 4 Investigation Reports

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
