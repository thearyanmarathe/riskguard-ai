"""Read-only Streamlit RiskGuard AI Investigation Console."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping

import pandas as pd
import streamlit as st
from sqlalchemy import text

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from behavioral_context import RULE_POINTS  # noqa: E402
from database import Database  # noqa: E402
from investigation_repository import InvestigationRepository  # noqa: E402

ASSESSMENT_PATH = PROJECT_ROOT / "reports" / "behavioral" / "behavioral_risk_assessments.csv"
MODEL_ARTIFACT_PATH = PROJECT_ROOT / "reports" / "model" / "xgboost_baseline.json"
RULE_DISPLAY_NAMES = {
    "high_transaction_velocity": "High transaction velocity",
    "unusual_device": "Unusual device",
    "unusual_region": "Unusual region",
    "high_transaction_amount": "High transaction amount",
    "high_amount_deviation": "High amount deviation",
}
REQUIRED_COLUMNS = {
    "source_row_id", "Time", "Amount", "Class", "user_id", "device_id", "region", "transaction_velocity",
    "ml_fraud_probability", "behavioral_rule_points", "ml_risk_points", "risk_score", "risk_level",
    "triggered_rules", "risk_explanation", "historical_average_amount", "amount_deviation",
    *[f"{rule}_triggered" for rule in RULE_POINTS],
    *[f"{rule}_explanation" for rule in RULE_POINTS],
}


@st.cache_data(show_spinner=False)
def load_assessments(path: str) -> pd.DataFrame:
    """Load saved Phase 3 data for contextual display only."""
    return pd.read_csv(path)


def build_repository() -> InvestigationRepository:
    """Build the existing repository used for read-only console queries."""
    return InvestigationRepository(Database())


def load_recent_investigations(repository: InvestigationRepository, limit: int = 100) -> list[dict[str, Any]]:
    """Read a bounded, deterministic recent-investigation set."""
    return repository.list_recent(limit=limit)


def lookup_source_investigation(repository: InvestigationRepository, source_row_id: int) -> dict[str, Any] | None:
    """Return the newest saved record for a bounded source row ID."""
    matches = repository.list_recent(limit=1, source_row_id=source_row_id)
    return matches[0] if matches else None


def summarize_investigations(records: list[Mapping[str, Any]]) -> dict[str, int]:
    """Summarize persisted records without deriving or changing risk values."""
    return {
        "total": len(records),
        "HIGH": sum(str(record.get("risk_level", "")).upper() == "HIGH" for record in records),
        "MEDIUM": sum(str(record.get("risk_level", "")).upper() == "MEDIUM" for record in records),
        "LOW": sum(str(record.get("risk_level", "")).upper() == "LOW" for record in records),
        "fallback": sum(bool(record.get("fallback_used")) for record in records),
        "provider": sum(bool(record.get("provider_used")) for record in records),
    }


def risk_distribution(records: list[Mapping[str, Any]]) -> pd.DataFrame:
    """Create a display frame from persisted risk-level values only."""
    counts = summarize_investigations(records)
    return pd.DataFrame({"Risk level": ["LOW", "MEDIUM", "HIGH"], "Investigations": [counts["LOW"], counts["MEDIUM"], counts["HIGH"]]}).set_index("Risk level")


def persisted_risk_distribution(repository: InvestigationRepository) -> pd.DataFrame:
    """Build the exact distribution from a repository aggregate query."""
    counts = repository.risk_level_counts()
    return pd.DataFrame({"Risk level": ["LOW", "MEDIUM", "HIGH"], "Investigations": [counts["LOW"], counts["MEDIUM"], counts["HIGH"]]}).set_index("Risk level")


def show_risk_level(level: str) -> None:
    messages = {
        "LOW": (st.success, "LOW RISK — no immediate escalation recommended."),
        "MEDIUM": (st.warning, "MEDIUM RISK — review the transaction and stored signals."),
        "HIGH": (st.error, "HIGH RISK — prioritize manual fraud investigation."),
    }
    component, message = messages.get(level, (st.info, f"Risk level: {level}"))
    component(message)


def rule_rows(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Format saved assessment rule status; no rule evaluation occurs here."""
    rows: list[dict[str, Any]] = []
    for rule, points in RULE_POINTS.items():
        if str(record.get(f"{rule}_triggered", "")).strip().lower() == "true":
            rows.append({"Rule": RULE_DISPLAY_NAMES[rule], "Triggered": "Yes", "Points": points, "Stored explanation": record.get(f"{rule}_explanation", "Stored rule explanation unavailable.")})
    return rows


def stored_rule_rows(record: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Format persisted triggered rules without recomputing points."""
    return [{"Rule": rule.get("rule_name", "Unnamed rule"), "Triggered": "Yes" if rule.get("triggered") else "No", "Points": rule.get("points", 0), "Stored explanation": rule.get("evidence", "Stored explanation unavailable.")} for rule in record.get("triggered_rules", [])]


def assessment_for_source(assessments: pd.DataFrame, source_row_id: int) -> dict[str, Any] | None:
    matches = assessments.loc[assessments["source_row_id"] == source_row_id]
    return None if matches.empty else matches.iloc[0].to_dict()


def safe_system_status(repository: InvestigationRepository) -> dict[str, str]:
    """Return non-sensitive component status for the status section."""
    try:
        with repository.database.engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        database_status = "Ready"
    except Exception:
        database_status = "Unavailable"
    return {
        "Database": database_status,
        "Saved assessments": "Available" if ASSESSMENT_PATH.exists() else "Unavailable",
        "Model artifact": "Available" if MODEL_ARTIFACT_PATH.exists() else "Unavailable",
        "AI mode": "Optional provider configured" if os.environ.get("AI_PROVIDER_API_KEY") else "Deterministic fallback",
    }


def _recent_frame(records: list[Mapping[str, Any]]) -> pd.DataFrame:
    return pd.DataFrame([{
        "Investigation ID": record["id"], "Source row ID": record["source_row_id"], "Created": record["created_at"],
        "Risk level": record["risk_level"], "Risk score": record["risk_score"], "ML probability": record["ml_fraud_probability"],
        "Behavioral points": record["behavioral_points"], "Provider mode": "Optional AI provider" if record["provider_used"] else "Deterministic fallback",
        "Fallback": "Yes" if record["fallback_used"] else "No",
    } for record in records])


def render_detail(record: Mapping[str, Any], assessment: Mapping[str, Any] | None, audit_events: list[Mapping[str, Any]]) -> None:
    """Render a persisted investigation; all values are read-only."""
    level = str(record["risk_level"]).upper()
    st.header(f"Investigation #{record['id']}")
    st.caption(f"Source row {record['source_row_id']} • Created {record['created_at']}")
    show_risk_level(level)
    metrics = st.columns(4)
    metrics[0].metric("Risk level", level)
    metrics[1].metric("Risk score", f"{float(record['risk_score']):.2f}")
    metrics[2].metric("ML fraud probability", f"{float(record['ml_fraud_probability']):.8f}")
    metrics[3].metric("Behavioral points", f"{float(record['behavioral_points']):.0f}")

    tabs = st.tabs(["Overview", "ML evidence", "Behavioral evidence", "Risk decision", "AI investigation", "Audit history"])
    with tabs[0]:
        st.subheader("Transaction context")
        if assessment is None:
            st.info("The saved assessment context is unavailable for this investigation.")
        else:
            st.caption("REAL KAGGLE DATA — dataset fields shown for context")
            st.dataframe(pd.DataFrame([{ "Source row ID": record["source_row_id"], "Time": assessment.get("Time"), "Amount": assessment.get("Amount"), "Class": assessment.get("Class") }]), hide_index=True, width="stretch")
        st.caption("SYNTHETIC DEMO BEHAVIORAL METADATA — not customer history or Kaggle fields")
        if assessment is None:
            st.info("Synthetic behavioral context is unavailable.")
        else:
            st.dataframe(pd.DataFrame([{
                "user_id": assessment.get("user_id"), "device_id": assessment.get("device_id"), "region": assessment.get("region"),
                "transaction_velocity": assessment.get("transaction_velocity"), "historical_average_amount": assessment.get("historical_average_amount"), "amount_deviation": assessment.get("amount_deviation"),
            }]), hide_index=True, width="stretch")
    with tabs[1]:
        st.subheader("ML evidence")
        st.metric("ML fraud probability", f"{float(record['ml_fraud_probability']):.8f}")
        st.info("This console displays the stored model result. It does not reload the model, recalculate predictions, or expose V1–V28 vectors.")
        st.caption("MODEL EXPLAINABILITY is informational; feature contribution is not causal evidence.")
    with tabs[2]:
        st.subheader("Behavioral signals")
        st.caption("SYNTHETIC DEMO BEHAVIORAL METADATA — rule outputs are stored application results.")
        rows = stored_rule_rows(record)
        if rows:
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
        else:
            st.info("No behavioral rules were triggered for this investigation.")
        st.metric("Stored behavioral points", f"{float(record['behavioral_points']):.0f}")
    with tabs[3]:
        st.subheader("Deterministic risk decision")
        st.metric("Risk score", f"{float(record['risk_score']):.2f}")
        st.metric("Risk level", level)
        st.write("The deterministic risk engine owns the risk decision.")
        if record.get("triggered_rules"):
            st.dataframe(pd.DataFrame(stored_rule_rows(record)), hide_index=True, width="stretch")
        else:
            st.info("No triggered rules stored.")
    with tabs[4]:
        st.subheader("AI Investigator")
        st.write(f"Provider: {'Optional AI provider' if record['provider_used'] else 'Deterministic fallback'}")
        st.write(f"Fallback active: {'Yes' if record['fallback_used'] else 'No'}")
        st.caption("ADVISORY — this explanation does not modify the deterministic risk decision.")
        st.write(record.get("investigation_summary", "No investigation summary is available."))
        st.write("Risk factors")
        for item in record.get("risk_factors", []):
            st.write(f"- {item}")
        st.write("Evidence")
        for item in record.get("evidence", []):
            st.write(f"- {item}")
        st.write(f"Recommended action: {record.get('recommended_action', 'Unavailable')} (advisory)")
        if record.get("confidence") is not None:
            st.write(f"Confidence: {float(record['confidence']):.2f}")
    with tabs[5]:
        st.subheader("Audit history")
        if audit_events:
            st.dataframe(pd.DataFrame([{"Event": event["event_type"], "Timestamp": event["created_at"], "Safe metadata": json.dumps(event.get("metadata", {}), sort_keys=True)} for event in audit_events]), hide_index=True, width="stretch")
        else:
            st.info("No audit events are available for this investigation.")


def main() -> None:
    st.set_page_config(page_title="RiskGuard AI | Investigation Console", page_icon="🛡️", layout="wide")
    st.title("RiskGuard AI")
    st.subheader("Risk Investigation Console")
    st.info("The console is presentation-only. It reads persisted application results and saved assessments; it does not calculate risk or write investigation records.")
    try:
        assessments = load_assessments(str(ASSESSMENT_PATH))
        if REQUIRED_COLUMNS.difference(assessments.columns):
            st.error("Saved assessment data is missing expected fields.")
            return
        repository = build_repository()
        recent = load_recent_investigations(repository, limit=100)
        persisted_distribution = persisted_risk_distribution(repository)
        persisted_counts = persisted_distribution["Investigations"].to_dict()
    except Exception:
        st.error("The investigation console could not load its saved data.")
        return

    counts = {"total": int(persisted_distribution["Investigations"].sum()), "LOW": int(persisted_counts["LOW"]), "MEDIUM": int(persisted_counts["MEDIUM"]), "HIGH": int(persisted_counts["HIGH"])}
    st.header("Overview")
    metrics = st.columns(4)
    for column, label, value in zip(metrics, ("Total investigations", "HIGH", "MEDIUM", "LOW"), (counts["total"], counts["HIGH"], counts["MEDIUM"], counts["LOW"])):
        column.metric(label, value)
    st.header("Risk distribution")
    if recent:
        st.bar_chart(persisted_distribution, width="stretch")
    else:
        st.info("No persisted investigations are available yet.")
    st.header("Recent investigations")
    if recent:
        st.dataframe(_recent_frame(recent), hide_index=True, width="stretch")
    else:
        st.info("Run an authenticated investigation through the existing application service to populate this console.")
    st.header("Investigation lookup")
    default_source_row = int(recent[0]["source_row_id"]) if recent else 0
    source_row_id = st.number_input("Source row ID", min_value=0, max_value=10_000_000, value=default_source_row, step=1)
    selected = lookup_source_investigation(repository, int(source_row_id)) if recent else None
    if selected is None:
        st.info("No persisted investigation was found for this source row.")
    else:
        assessment = assessment_for_source(assessments, int(selected["source_row_id"]))
        try:
            events = repository.list_events(int(selected["id"]))
        except Exception:
            events = []
            st.warning("Audit history is temporarily unavailable.")
        render_detail(selected, assessment, events)
    st.header("System status")
    st.dataframe(pd.DataFrame([safe_system_status(repository)]), hide_index=True, width="stretch")
    st.caption("AI provider credentials, database paths, prompts, raw CSV rows, and anonymized V1–V28 vectors are never displayed.")
    repository.database.close()


if __name__ == "__main__":
    main()
