"""Read-only Streamlit RiskGuard AI Investigation Console."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any, Mapping

import altair as alt
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
RISK_COLORS = {"LOW": "#3DDC97", "MEDIUM": "#F5C542", "HIGH": "#F07167"}
CONSOLE_CSS = """
<style>
    .stApp { background: radial-gradient(1200px 600px at 10% -10%, #1a2744 0%, #0B1220 45%); }
    [data-testid="stSidebar"] { background: #101828; border-right: 1px solid #243049; }
    .rg-kicker { letter-spacing: 0.14em; text-transform: uppercase; font-size: 0.72rem; color: #8BA0C4; margin-bottom: 0.2rem; }
    .rg-badge { display: inline-block; padding: 0.2rem 0.7rem; border-radius: 999px; font-weight: 700; font-size: 0.78rem; letter-spacing: 0.06em; }
    .rg-badge-low { background: rgba(61, 220, 151, 0.18); color: #3DDC97; border: 1px solid #3DDC97; }
    .rg-badge-medium { background: rgba(245, 197, 66, 0.18); color: #F5C542; border: 1px solid #F5C542; }
    .rg-badge-high { background: rgba(240, 113, 103, 0.18); color: #F07167; border: 1px solid #F07167; }
    .rg-chip { display: inline-block; padding: 0.15rem 0.55rem; border-radius: 6px; background: #1E2A44; color: #C5D4F0; font-size: 0.78rem; margin-right: 0.4rem; }
    .rg-status { font-size: 0.85rem; color: #C5D4F0; line-height: 1.7; }
    .rg-card { border: 1px solid #243049; background: #151D2E; border-radius: 12px; padding: 0.85rem 1rem; margin-bottom: 0.75rem; }
    div[data-testid="stMetric"] { background: #151D2E; border: 1px solid #243049; border-radius: 12px; padding: 0.75rem 0.9rem; }
</style>
"""


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


def inject_theme() -> None:
    """Apply the local risk-ops presentation theme."""
    st.markdown(CONSOLE_CSS, unsafe_allow_html=True)


def _badge_class(level: str) -> str:
    return {"LOW": "rg-badge rg-badge-low", "MEDIUM": "rg-badge rg-badge-medium", "HIGH": "rg-badge rg-badge-high"}.get(level, "rg-badge")


def _selected_rows(event: Any) -> list[int]:
    """Read Streamlit dataframe row selection without depending on a single return type."""
    selection = event.selection if hasattr(event, "selection") else event.get("selection") if isinstance(event, dict) else None
    if selection is None:
        return []
    rows = selection.rows if hasattr(selection, "rows") else selection.get("rows", []) if isinstance(selection, dict) else []
    return [int(index) for index in (rows or [])]


def render_distribution_chart(distribution: pd.DataFrame) -> None:
    """Display persisted LOW/MEDIUM/HIGH counts with fixed risk colors."""
    frame = distribution.reset_index()
    color_scale = alt.Scale(domain=["LOW", "MEDIUM", "HIGH"], range=[RISK_COLORS["LOW"], RISK_COLORS["MEDIUM"], RISK_COLORS["HIGH"]])
    chart = (
        alt.Chart(frame)
        .mark_bar(size=48, cornerRadiusEnd=6)
        .encode(
            x=alt.X("Risk level:N", sort=["LOW", "MEDIUM", "HIGH"], title=None),
            y=alt.Y("Investigations:Q", title="Investigations"),
            color=alt.Color("Risk level:N", scale=color_scale, legend=None),
            tooltip=["Risk level", "Investigations"],
        )
        .properties(height=280)
    )
    st.altair_chart(chart, width="stretch")


def render_sidebar(status: Mapping[str, str]) -> str:
    """Render navigation and compact, non-sensitive system status."""
    with st.sidebar:
        st.markdown('<div class="rg-kicker">RiskGuard AI</div>', unsafe_allow_html=True)
        st.markdown("**Investigation console**")
        st.caption("Read-only presentation of persisted assessments and investigations.")
        view = st.radio("Workspace", ("Overview", "Investigation"), key="console_view")
        st.divider()
        st.markdown("**System status**")
        lines = "<br>".join(f"{label}: {value}" for label, value in status.items())
        st.markdown(f'<div class="rg-status">{lines}</div>', unsafe_allow_html=True)
        st.caption("Credentials, database paths, prompts, raw CSV rows, and V1–V28 vectors are never displayed.")
    return str(view)


def render_overview(recent: list[Mapping[str, Any]], persisted_distribution: pd.DataFrame, counts: Mapping[str, int]) -> None:
    """Overview workspace: KPIs, distribution, and selectable recent cases."""
    st.markdown('<div class="rg-kicker">Workspace</div>', unsafe_allow_html=True)
    st.title("Overview")
    st.caption("Persisted investigation volume and risk-level mix. Values are stored application results.")
    metrics = st.columns(4)
    for column, label, value in zip(metrics, ("Total investigations", "HIGH", "MEDIUM", "LOW"), (counts["total"], counts["HIGH"], counts["MEDIUM"], counts["LOW"])):
        column.metric(label, value)

    st.subheader("Risk distribution")
    if recent:
        render_distribution_chart(persisted_distribution)
    else:
        st.info("No persisted investigations are available yet.")

    st.subheader("Recent investigations")
    if not recent:
        st.info("Run an authenticated investigation through the existing application service to populate this console.")
        return

    frame = _recent_frame(recent)
    st.caption("Select a row to open it in the Investigation workspace.")
    event = st.dataframe(frame, hide_index=True, width="stretch", on_select="rerun", selection_mode="single-row", key="recent_investigations")
    selected_rows = _selected_rows(event)
    if not selected_rows:
        return
    row_index = int(selected_rows[0])
    source_id = int(frame.iloc[row_index]["Source row ID"])
    if st.session_state.get("last_overview_selection") == row_index and st.session_state.get("console_view") == "Investigation":
        return
    if st.session_state.get("last_overview_selection") != row_index:
        st.session_state.last_overview_selection = row_index
        st.session_state.lookup_source_row = source_id
        st.session_state.console_view = "Investigation"
        st.rerun()


def render_detail(record: Mapping[str, Any], assessment: Mapping[str, Any] | None, audit_events: list[Mapping[str, Any]]) -> None:
    """Render a persisted investigation; all values are read-only."""
    level = str(record["risk_level"]).upper()
    stored_score = float(record["risk_score"])
    heading, badge = st.columns([4, 1])
    heading.header(f"Investigation #{record['id']}")
    heading.caption(f"Source row {record['source_row_id']} • Created {record['created_at']}")
    badge.markdown(f'<div style="text-align:right;margin-top:1.4rem;"><span class="{_badge_class(level)}">{level}</span></div>', unsafe_allow_html=True)
    show_risk_level(level)

    metrics = st.columns(4)
    metrics[0].metric("Risk level", level)
    metrics[1].metric("Risk score", f"{stored_score:.2f}")
    metrics[2].metric("ML fraud probability", f"{float(record['ml_fraud_probability']):.8f}")
    metrics[3].metric("Behavioral points", f"{float(record['behavioral_points']):.0f}")
    st.caption("Stored risk score (0–100 display scale; the engine owns the value).")
    st.progress(min(1.0, max(0.0, stored_score / 100.0)))

    tabs = st.tabs(["Overview", "ML evidence", "Behavioral evidence", "Risk decision", "AI investigation", "Audit history"])
    with tabs[0]:
        left, right = st.columns(2)
        with left:
            st.subheader("Transaction context")
            if assessment is None:
                st.info("The saved assessment context is unavailable for this investigation.")
            else:
                st.caption("REAL KAGGLE DATA — dataset fields shown for context")
                st.dataframe(pd.DataFrame([{ "Source row ID": record["source_row_id"], "Time": assessment.get("Time"), "Amount": assessment.get("Amount"), "Class": assessment.get("Class") }]), hide_index=True, width="stretch")
        with right:
            st.subheader("Behavioral metadata")
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
        decision = st.columns(2)
        decision[0].metric("Risk score", f"{stored_score:.2f}")
        decision[1].metric("Risk level", level)
        st.write("The deterministic risk engine owns the risk decision.")
        if record.get("triggered_rules"):
            st.dataframe(pd.DataFrame(stored_rule_rows(record)), hide_index=True, width="stretch")
        else:
            st.info("No triggered rules stored.")
    with tabs[4]:
        st.subheader("AI Investigator")
        provider_label = "Optional AI provider" if record["provider_used"] else "Deterministic fallback"
        fallback_label = "Yes" if record["fallback_used"] else "No"
        st.markdown(
            f'<span class="rg-chip">Provider: {provider_label}</span>'
            f'<span class="rg-chip">Fallback active: {fallback_label}</span>',
            unsafe_allow_html=True,
        )
        st.caption("ADVISORY — this explanation does not modify the deterministic risk decision.")
        st.info(str(record.get("investigation_summary", "No investigation summary is available.")))
        factors = list(record.get("risk_factors") or [])
        evidence = list(record.get("evidence") or [])
        lists = st.columns(2)
        with lists[0]:
            st.markdown("**Risk factors**")
            if factors:
                st.markdown("\n".join(f"- {item}" for item in factors))
            else:
                st.caption("No stored risk factors.")
        with lists[1]:
            st.markdown("**Evidence**")
            if evidence:
                st.markdown("\n".join(f"- {item}" for item in evidence))
            else:
                st.caption("No stored evidence items.")
        st.markdown(f"**Recommended action:** {record.get('recommended_action', 'Unavailable')} (advisory)")
        if record.get("confidence") is not None:
            st.markdown(f"**Confidence:** {float(record['confidence']):.2f}")
    with tabs[5]:
        st.subheader("Audit history")
        if audit_events:
            st.dataframe(pd.DataFrame([{"Event": event["event_type"], "Timestamp": event["created_at"], "Safe metadata": json.dumps(event.get("metadata", {}), sort_keys=True)} for event in audit_events]), hide_index=True, width="stretch")
        else:
            st.info("No audit events are available for this investigation.")


def render_investigation_workspace(
    repository: InvestigationRepository,
    assessments: pd.DataFrame,
    recent: list[Mapping[str, Any]],
) -> None:
    """Investigation workspace: lookup plus detail for a persisted source row."""
    st.markdown('<div class="rg-kicker">Workspace</div>', unsafe_allow_html=True)
    st.title("Investigation")
    st.caption("Lookup a persisted source row. The console does not calculate risk or write records.")
    default_source_row = int(recent[0]["source_row_id"]) if recent else 0
    if "lookup_source_row" not in st.session_state:
        st.session_state.lookup_source_row = default_source_row
    source_row_id = st.number_input("Source row ID", min_value=0, max_value=10_000_000, step=1, key="lookup_source_row")
    selected = lookup_source_investigation(repository, int(source_row_id)) if recent else None
    if selected is None:
        st.info("No persisted investigation was found for this source row." if recent else "Run an authenticated investigation through the existing application service to populate this console.")
        return
    assessment = assessment_for_source(assessments, int(selected["source_row_id"]))
    try:
        events = repository.list_events(int(selected["id"]))
    except Exception:
        events = []
        st.warning("Audit history is temporarily unavailable.")
    render_detail(selected, assessment, events)


def main() -> None:
    st.set_page_config(page_title="RiskGuard AI | Investigation Console", page_icon="🛡️", layout="wide")
    inject_theme()
    if "console_view" not in st.session_state:
        st.session_state.console_view = "Overview"
    try:
        assessments = load_assessments(str(ASSESSMENT_PATH))
        if REQUIRED_COLUMNS.difference(assessments.columns):
            st.error("Saved assessment data is missing expected fields.")
            return
        repository = build_repository()
        recent = load_recent_investigations(repository, limit=100)
        persisted_distribution = persisted_risk_distribution(repository)
        persisted_counts = persisted_distribution["Investigations"].to_dict()
        status = safe_system_status(repository)
    except Exception:
        st.error("The investigation console could not load its saved data.")
        return

    view = render_sidebar(status)
    counts = {"total": int(persisted_distribution["Investigations"].sum()), "LOW": int(persisted_counts["LOW"]), "MEDIUM": int(persisted_counts["MEDIUM"]), "HIGH": int(persisted_counts["HIGH"])}
    if view == "Overview":
        render_overview(recent, persisted_distribution, counts)
    else:
        render_investigation_workspace(repository, assessments, recent)
    repository.database.close()


if __name__ == "__main__":
    main()
