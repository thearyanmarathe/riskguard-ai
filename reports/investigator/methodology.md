# RiskGuard AI — Phase 4 Investigator Methodology

The application Investigator first constructs the existing deterministic report from a fixed whitelist of fields already present in the Phase 3 assessment. If `AI_PROVIDER_API_KEY` is configured, the guarded optional provider may add a validated advisory explanation. Without a key, or after any provider failure or invalid output, the deterministic report is returned.

The deterministic path uses no generative text, no extra transaction data, and no inferred facts. Its rule evidence is copied from the existing rule-engine explanation fields. Deterministic recommendations are fixed by the supplied risk level: LOW has no immediate escalation, MEDIUM recommends review, and HIGH recommends prioritised manual investigation. Every report states that it does not prove fraud.

The deterministic risk level, score, ML probability, behavioral points, and stored rule evidence remain authoritative. The provider cannot execute actions or change those values; recommendations are advisory only. Provider input is minimized and excludes raw model features, labels, and synthetic identifiers.

Synthetic `user_id`, `device_id`, `region`, `transaction_velocity`, `historical_average_amount`, and `amount_deviation` are always labelled as demo metadata, not real Kaggle customer information. The raw CSV is never read or modified by this phase.
