"""Streamlit UI for the existing RiskGuard AI Phase 2–4 outputs.

Run from the project root:
    .venv\\Scripts\\python -m streamlit run .\\scripts\\app.py

This is a presentation layer only: it reads saved Phase 3 assessments and
reuses the Phase 4 investigator. It does not train, score, or alter data.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st


SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from behavioral_context import RULE_POINTS
from investigator import DeterministicInvestigator


ASSESSMENT_PATH = PROJECT_ROOT / "reports" / "behavioral" / "behavioral_risk_assessments.csv"
MODEL_ARTIFACT_PATH = PROJECT_ROOT / "reports" / "model" / "xgboost_baseline.json"
RULE_DISPLAY_NAMES = {
    "high_transaction_velocity": "High transaction velocity",
    "unusual_device": "Unusual device",
    "unusual_region": "Unusual region",
    "high_transaction_amount": "High transaction amount",
}
REQUIRED_COLUMNS = {
    "source_row_id", "Time", "Amount", "Class", "user_id", "device_id", "region", "transaction_velocity",
    "ml_fraud_probability", "behavioral_rule_points", "ml_risk_points", "risk_score", "risk_level",
    "triggered_rules", "risk_explanation",
    *[f"{rule}_triggered" for rule in RULE_POINTS],
    *[f"{rule}_explanation" for rule in RULE_POINTS],
}


@st.cache_data(show_spinner=False)
def load_assessments(path: str) -> pd.DataFrame:
    """Load immutable Phase 3 output for UI display."""
    return pd.read_csv(path)


def show_risk_level(level: str) -> None:
    """Use a visible status component without changing assessment logic."""
    messages = {
        "LOW": (st.success, "LOW RISK — no immediate escalation recommended."),
        "MEDIUM": (st.warning, "MEDIUM RISK — review the transaction and triggered behavioral signals."),
        "HIGH": (st.error, "HIGH RISK — prioritize this transaction for manual fraud investigation."),
    }
    component, message = messages.get(level, (st.info, f"Risk level: {level}"))
    component(message)


def rule_rows(record: dict) -> list[dict]:
    """Format saved rule-engine output for display; no rule evaluation occurs here."""
    rows = []
    for rule, points in RULE_POINTS.items():
        if str(record[f"{rule}_triggered"]).strip().lower() == "true":
            rows.append(
                {
                    "Rule": RULE_DISPLAY_NAMES[rule],
                    "Triggered": "Yes",
                    "Points": points,
                    "Stored explanation": record[f"{rule}_explanation"],
                }
            )
    return rows


def main() -> None:
    st.set_page_config(page_title="RiskGuard AI", page_icon="🛡️", layout="wide")
    st.title("RiskGuard AI")
    st.caption("AI-assisted credit card fraud risk investigation")
    st.info("Behavioral user, device, region, and velocity fields are **synthetic demonstration metadata**. They are not Kaggle customer data.")

    if not ASSESSMENT_PATH.exists():
        st.error(
            f"Behavioral assessment file is missing: `{ASSESSMENT_PATH.relative_to(PROJECT_ROOT)}`. "
            "Run `scripts/run_behavioral_demo.py` before opening the dashboard."
        )
        st.stop()
    if not MODEL_ARTIFACT_PATH.exists():
        st.warning(
            "The saved XGBoost artifact is missing. Existing assessment results can still be displayed, "
            "but rerun `scripts/train_baselines.py` then `scripts/run_behavioral_demo.py` to restore the full pipeline."
        )

    try:
        assessments = load_assessments(str(ASSESSMENT_PATH))
    except (OSError, pd.errors.ParserError) as error:
        st.error(f"Could not read the behavioral assessment file: {error}")
        st.stop()
    missing_columns = REQUIRED_COLUMNS.difference(assessments.columns)
    if missing_columns:
        st.error("Behavioral assessment is missing expected columns: " + ", ".join(sorted(missing_columns)))
        st.stop()
    if assessments.empty:
        st.error("Behavioral assessment contains no transactions.")
        st.stop()

    assessments["source_row_id"] = assessments["source_row_id"].astype(int)
    row_ids = sorted(assessments["source_row_id"].tolist())
    highest_risk_id = int(assessments.sort_values(["risk_score", "source_row_id"], ascending=[False, True]).iloc[0]["source_row_id"])
    default_index = row_ids.index(highest_risk_id)

    with st.sidebar:
        st.header("Transaction selector")
        selected_id = st.selectbox("Select source row ID", row_ids, index=default_index)
        manual_id = st.text_input("Or enter a source row ID", placeholder="e.g. 215984")
        if manual_id.strip():
            try:
                selected_id = int(manual_id)
            except ValueError:
                st.error("Enter a whole-number source row ID.")
                st.stop()
        st.caption("Only transactions already present in the saved Phase 3 assessment can be investigated.")

    selected = assessments.loc[assessments["source_row_id"] == selected_id]
    if selected.empty:
        st.error(f"Source row ID {selected_id} is not available in the saved behavioral assessment.")
        st.stop()
    record = selected.iloc[0].to_dict()
    risk_level = str(record["risk_level"]).upper()

    st.subheader(f"Transaction investigation — source row {selected_id}")
    show_risk_level(risk_level)

    st.header("Risk summary")
    metric_columns = st.columns(4)
    metric_columns[0].metric("Risk level", risk_level)
    metric_columns[1].metric("Risk score", f"{float(record['risk_score']):.2f}")
    metric_columns[2].metric("ML fraud probability", f"{float(record['ml_fraud_probability']):.6f}")
    metric_columns[3].metric("Transaction amount", f"{float(record['Amount']):,.2f}")

    left, right = st.columns(2)
    with left:
        st.header("Transaction details")
        st.dataframe(
            pd.DataFrame(
                [{"Source row ID": selected_id, "Time": record["Time"], "Amount": record["Amount"], "Class": record["Class"]}]
            ),
            hide_index=True,
            width="stretch",
        )
        st.caption("`Class` is the available Kaggle dataset label; this dashboard does not treat it as proof of fraud.")
    with right:
        st.header("Behavioral context")
        st.caption("Synthetic demo metadata — not real Kaggle customer information")
        st.dataframe(
            pd.DataFrame(
                [{
                    "user_id": record["user_id"], "device_id": record["device_id"], "region": record["region"],
                    "transaction_velocity": record["transaction_velocity"],
                }]
            ),
            hide_index=True,
            width="stretch",
        )

    st.header("Triggered behavioral rules")
    triggered = rule_rows(record)
    if triggered:
        st.dataframe(pd.DataFrame(triggered), hide_index=True, width="stretch")
    else:
        st.info("No behavioral rules were triggered for this transaction.")

    st.header("Signal contributions")
    contributions = [{"Signal": "ML probability × 60", "Risk points": float(record["ml_risk_points"])}]
    contributions.extend({"Signal": row["Rule"], "Risk points": row["Points"]} for row in triggered)
    st.bar_chart(pd.DataFrame(contributions).set_index("Signal"), width="stretch")
    st.caption("Displayed contributions use the saved transparent formula; the dashboard does not recalculate risk.")

    st.header("AI Investigator")
    try:
        investigation = DeterministicInvestigator().investigate(record)
    except (TypeError, ValueError) as error:
        st.error(f"The selected transaction could not be investigated: {error}")
        st.stop()
    st.subheader("Investigation summary")
    st.write(investigation["investigation_summary"])
    st.subheader("Key risk signals")
    for signal in investigation["key_risk_signals"]:
        st.write(f"- {signal}")
    st.subheader("Evidence")
    if investigation["triggered_behavioral_rules"]:
        for rule in investigation["triggered_behavioral_rules"]:
            st.write(f"- **{rule['rule_name']}**: {rule['evidence']}")
    else:
        st.write("- No behavioral rules were triggered.")
    st.subheader("Recommended action")
    st.write(investigation["recommended_investigation_action"])
    st.caption(investigation["evidence_boundary"])


if __name__ == "__main__":
    main()
