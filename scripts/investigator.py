"""Deterministic, evidence-only investigator for Phase 4.

This module deliberately has no LLM or external-service dependency. It uses a
whitelist of fields already present in a Phase 3 assessment and never infers
customer history, motives, locations, or account status.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


RULES = (
    ("high_transaction_velocity", "High transaction velocity"),
    ("unusual_device", "Unusual device"),
    ("unusual_region", "Unusual region"),
    ("high_transaction_amount", "High transaction amount"),
)
RECOMMENDATIONS = {
    "LOW": "No immediate escalation recommended.",
    "MEDIUM": "Review the transaction and triggered behavioral signals.",
    "HIGH": "Prioritize this transaction for manual fraud investigation.",
}
REQUIRED_FIELDS = {
    "source_row_id", "Time", "Amount", "ml_fraud_probability", "behavioral_rule_points",
    "risk_score", "risk_level", "triggered_rules", "risk_explanation",
}


def _as_bool(value: Any) -> bool:
    """Interpret CSV and pandas boolean values without accepting ambiguity."""
    if isinstance(value, str):
        return value.strip().lower() == "true"
    return bool(value)


class DeterministicInvestigator:
    """Render a structured report from supplied Phase 3 evidence only."""

    def investigate(self, record: Mapping[str, Any]) -> dict[str, Any]:
        """Investigate one assessment record without adding facts not in it."""
        missing_fields = REQUIRED_FIELDS.difference(record)
        if missing_fields:
            raise ValueError(f"Assessment is missing required fields: {sorted(missing_fields)}")

        risk_level = str(record["risk_level"]).upper()
        if risk_level not in RECOMMENDATIONS:
            raise ValueError(f"Unsupported risk level: {risk_level}")

        triggered_rules = []
        for key, name in RULES:
            trigger_key = f"{key}_triggered"
            explanation_key = f"{key}_explanation"
            if trigger_key in record and _as_bool(record[trigger_key]):
                triggered_rules.append(
                    {
                        "rule_name": name,
                        "triggered": True,
                        "evidence": str(record.get(explanation_key, "No stored rule explanation available.")),
                    }
                )

        probability = float(record["ml_fraud_probability"])
        rule_points = float(record["behavioral_rule_points"])
        risk_score = float(record["risk_score"])
        key_signals = [
            f"Saved Phase 2 XGBoost baseline fraud probability: {probability:.6f}.",
            f"Transparent risk score: {risk_score:.2f} ({risk_level}).",
            f"Behavioral-rule points: {rule_points:.0f}.",
        ]
        if triggered_rules:
            key_signals.append("Triggered behavioral rules: " + ", ".join(rule["rule_name"] for rule in triggered_rules) + ".")
        else:
            key_signals.append("No behavioral rules were triggered.")

        summary = (
            f"Source row {int(record['source_row_id'])} has a {risk_level} transparent risk assessment "
            f"with score {risk_score:.2f}. The saved XGBoost baseline output is {probability:.6f}, "
            f"and triggered behavioral rules contribute {rule_points:.0f} points. "
            "This identifies signals for review; it does not prove fraud."
        )
        return {
            "transaction": {
                "source_row_id": int(record["source_row_id"]),
                "time": float(record["Time"]),
                "amount": float(record["Amount"]),
            },
            "risk_assessment": {
                "risk_level": risk_level,
                "risk_score": risk_score,
                "ml_fraud_probability": probability,
                "behavioral_rule_points": rule_points,
                "risk_explanation": str(record["risk_explanation"]),
            },
            "synthetic_demo_context": {
                "user_id": str(record.get("user_id", "not supplied")),
                "device_id": str(record.get("device_id", "not supplied")),
                "region": str(record.get("region", "not supplied")),
                "transaction_velocity": int(record["transaction_velocity"]) if "transaction_velocity" in record else None,
                "disclaimer": "These fields are synthetic demo metadata, not Kaggle customer data.",
            },
            "key_risk_signals": key_signals,
            "triggered_behavioral_rules": triggered_rules,
            "investigation_summary": summary,
            "recommended_investigation_action": RECOMMENDATIONS[risk_level],
            "evidence_boundary": (
                "This deterministic report uses only supplied assessment fields and stored rule explanations. "
                "It does not infer customer history, location, motive, account compromise, or proof of fraud."
            ),
        }


def report_to_markdown(report: Mapping[str, Any]) -> str:
    """Render an investigator result as a concise human-readable report."""
    transaction = report["transaction"]
    risk = report["risk_assessment"]
    context = report["synthetic_demo_context"]
    rules = report["triggered_behavioral_rules"]
    rule_lines = "\n".join(f"- **{rule['rule_name']}**: {rule['evidence']}" for rule in rules) or "- No behavioral rules triggered."
    signal_lines = "\n".join(f"- {signal}" for signal in report["key_risk_signals"])
    return f"""## Investigation: Source Row {transaction['source_row_id']}

| Field | Value |
| --- | --- |
| Risk level | {risk['risk_level']} |
| Risk score | {risk['risk_score']:.2f} |
| ML fraud probability | {risk['ml_fraud_probability']:.6f} |
| Time | {transaction['time']:.2f} |
| Amount | {transaction['amount']:.2f} |

### Key risk signals

{signal_lines}

### Triggered behavioral rules and evidence

{rule_lines}

### Synthetic demo context

- User: `{context['user_id']}`; device: `{context['device_id']}`; region: `{context['region']}`; velocity: {context['transaction_velocity']}.
- {context['disclaimer']}

### Investigation summary

{report['investigation_summary']}

### Recommended action

{report['recommended_investigation_action']}

### Evidence boundary

{report['evidence_boundary']}
"""
