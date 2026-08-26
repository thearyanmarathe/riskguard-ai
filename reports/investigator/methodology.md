# RiskGuard AI — Phase 4 Investigator Methodology

The investigator is deterministic and does not use an LLM or an external API. It accepts one Phase 3 assessment record and constructs a report from a fixed whitelist of fields already present in that record: source row, `Time`, `Amount`, ML probability, risk values, synthetic demo context, rule triggers, and stored rule explanations.

It uses no generative text, no extra transaction data, and no inferred facts. The rule evidence is copied from the existing rule-engine explanation fields. Recommendations are fixed by the supplied risk level: LOW has no immediate escalation, MEDIUM recommends review, and HIGH recommends prioritised manual investigation. Every report states that it does not prove fraud.

An LLM could later be added behind an interface taking this structured report as input, with instructions to restate only supplied evidence. The deterministic investigator remains the default fallback and requires no API key.

Synthetic `user_id`, `device_id`, `region`, and `transaction_velocity` are always labelled as demo metadata, not real Kaggle customer information. The raw CSV is never read or modified by this phase.
