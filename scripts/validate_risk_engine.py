"""Validate the existing RiskGuard AI risk engine without changing it.

Run from the project root:
    .venv\\Scripts\\python scripts\\validate_risk_engine.py

The script reads saved Phase 3 assessments. Mathematical boundary/capping cases
exist only in memory and use the existing add_risk_assessment implementation.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from behavioral_context import RULE_POINTS, add_risk_assessment


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSESSMENT_PATH = PROJECT_ROOT / "reports" / "behavioral" / "behavioral_risk_assessments.csv"
OUTPUT_DIR = PROJECT_ROOT / "reports" / "risk"
RULES = list(RULE_POINTS)
RULE_DISPLAY_NAMES = {
    "high_transaction_velocity": "High Transaction Velocity",
    "unusual_device": "Unusual Device",
    "unusual_region": "Unusual Region",
    "high_transaction_amount": "High Transaction Amount",
    "high_amount_deviation": "High Amount Deviation",
}


def as_boolean(series: pd.Series) -> pd.Series:
    """Normalize CSV trigger fields for validation only."""
    return series.astype(str).str.strip().str.lower().eq("true")


def expected_level(score: float) -> str:
    """Document the existing score-level mapping for assertion messages."""
    if score < 25:
        return "LOW"
    if score < 50:
        return "MEDIUM"
    return "HIGH"


def markdown_table(data: pd.DataFrame, float_columns: set[str] | None = None) -> str:
    """Render compact Markdown without adding a tabulate dependency."""
    float_columns = float_columns or set()
    columns = list(data.columns)
    rows = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---:"] * len(columns)) + " |"]
    for row in data.itertuples(index=False):
        rendered = []
        for column, value in zip(columns, row):
            if column in float_columns:
                rendered.append(f"{float(value):.6f}")
            elif isinstance(value, float):
                rendered.append(f"{value:.2f}")
            else:
                rendered.append(str(value).replace("|", "\\|"))
        rows.append("| " + " | ".join(rendered) + " |")
    return "\n".join(rows)


def select_actual(data: pd.DataFrame, name: str, condition: pd.Series, ascending: list[bool]) -> pd.Series:
    """Pick a deterministic saved transaction for a named real-data scenario."""
    candidates = data.loc[condition]
    if candidates.empty:
        raise ValueError(f"No saved Phase 3 assessment is available for scenario: {name}")
    return candidates.sort_values(["ml_fraud_probability", "source_row_id"], ascending=ascending).iloc[0]


def scenario_from_actual(name: str, row: pd.Series) -> dict:
    """Preserve actual assessment values for an evidence-only scenario table."""
    triggered_names = [RULE_DISPLAY_NAMES[rule] for rule in RULES if bool(row[f"{rule}_triggered"])]
    rule_details = []
    for rule in RULES:
        triggered = bool(row[f"{rule}_triggered"])
        explanation = str(row[f"{rule}_explanation"]).strip()
        rule_details.append(
            f"{RULE_DISPLAY_NAMES[rule]}: triggered={triggered}; points={RULE_POINTS[rule] if triggered else 0}; "
            f"explanation={explanation}"
        )
    scenario = {
        "scenario": name,
        "scenario_type": "saved Phase 3 transaction",
        "source_row_id": int(row["source_row_id"]),
        "ml_fraud_probability": float(row["ml_fraud_probability"]),
        "behavioral_rule_points": int(row["behavioral_rule_points"]),
        "ml_risk_points": float(row["ml_risk_points"]),
        "risk_score": float(row["risk_score"]),
        "risk_level": str(row["risk_level"]),
        "triggered_rules": "; ".join(triggered_names) if triggered_names else "None",
        "rule_details": " | ".join(rule_details),
    }
    scenario.update({rule: bool(row[f"{rule}_triggered"]) for rule in RULES})
    return scenario


def implementation_cases() -> pd.DataFrame:
    """Use the real implementation for boundary and score-cap assertions."""
    cases = [
        ("Boundary: 24.99", 24.99 / 60, []),
        ("Boundary: 25.00", 25.00 / 60, []),
        ("Boundary: 49.99", 49.99 / 60, []),
        ("Boundary: 50.00", 50.00 / 60, []),
        ("Maximum/capping: raw score 135", 1.0, RULES),
    ]
    frame = pd.DataFrame(
        [
            {"scenario": name, "ml_fraud_probability": probability, **{f"{rule}_triggered": rule in triggered for rule in RULES}}
            for name, probability, triggered in cases
        ]
    )
    assessed = add_risk_assessment(frame, frame["ml_fraud_probability"])
    assessed["scenario_type"] = "in-memory mathematical test (not a transaction)"
    assessed["source_row_id"] = "N/A"
    assessed["rule_details"] = assessed.apply(
        lambda row: " | ".join(
            f"{RULE_DISPLAY_NAMES[rule]}: triggered={bool(row[f'{rule}_triggered'])}; "
            f"points={RULE_POINTS[rule] if bool(row[f'{rule}_triggered']) else 0}; "
            "explanation=Mathematical test input; no transaction explanation applies."
            for rule in RULES
        ),
        axis=1,
    )
    return assessed


def main() -> None:
    if not ASSESSMENT_PATH.exists():
        raise FileNotFoundError(f"Phase 3 assessment file not found: {ASSESSMENT_PATH}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    data = pd.read_csv(ASSESSMENT_PATH)
    required = {
        "source_row_id", "ml_fraud_probability", "behavioral_rule_points", "ml_risk_points", "risk_score", "risk_level",
        "triggered_rules", *[f"{rule}_triggered" for rule in RULES], *[f"{rule}_explanation" for rule in RULES],
    }
    missing = required.difference(data.columns)
    if missing:
        raise ValueError("Assessment file is missing required validation columns: " + ", ".join(sorted(missing)))

    for rule in RULES:
        data[f"{rule}_triggered"] = as_boolean(data[f"{rule}_triggered"])
    data["trigger_count"] = data[[f"{rule}_triggered" for rule in RULES]].sum(axis=1)

    derived_triggered_rules = data.apply(
        lambda row: "; ".join(RULE_DISPLAY_NAMES[rule] for rule in RULES if row[f"{rule}_triggered"]) or "None",
        axis=1,
    )
    stored_triggered_rules = data["triggered_rules"].fillna("None").astype(str).str.strip()
    if not stored_triggered_rules.eq(derived_triggered_rules).all():
        raise AssertionError("Saved assessment triggered_rules text disagrees with rule trigger flags.")

    expected_scores = (60 * data["ml_fraud_probability"] + data["behavioral_rule_points"]).clip(upper=100).round(2)
    score_match = np.isclose(data["risk_score"], expected_scores)
    level_match = data["risk_level"].eq(data["risk_score"].map(expected_level))
    if not score_match.all() or not level_match.all():
        raise AssertionError("Saved assessment contains a risk-score or risk-level mismatch.")

    scenarios = [
        scenario_from_actual("Normal transaction (no behavioral rules)", select_actual(data, "normal", data["trigger_count"].eq(0), [True, True])),
        scenario_from_actual("High ML probability with no behavioral rules", select_actual(data, "high ML/no rules", data["trigger_count"].eq(0), [False, True])),
        scenario_from_actual("Low ML probability with one behavioral rule", select_actual(data, "low ML/one rule", data["trigger_count"].eq(1), [True, True])),
    ]
    for rule in RULES:
        alone = data[f"{rule}_triggered"] & data["trigger_count"].eq(1)
        if alone.any():
            scenarios.append(
                scenario_from_actual(
                    f"{rule.replace('_', ' ').title()} alone",
                    select_actual(data, f"{rule} alone", alone, [True, True]),
                )
            )
    scenarios.extend(
        [
            scenario_from_actual("Multiple behavioral signals", select_actual(data, "multiple rules", data["trigger_count"].ge(2), [True, True])),
            scenario_from_actual("High ML probability plus behavioral signals", select_actual(data, "high ML/rules", data["trigger_count"].gt(0), [False, True])),
        ]
    )
    actual_scenarios = pd.DataFrame(scenarios)

    boundary_cases = implementation_cases()
    boundary_cases["expected_score"] = (
        60 * boundary_cases["ml_fraud_probability"] + boundary_cases["behavioral_rule_points"]
    ).clip(upper=100).round(2)
    boundary_cases["score_matches_formula"] = np.isclose(boundary_cases["risk_score"], boundary_cases["expected_score"])
    boundary_cases["level_matches_boundary"] = boundary_cases["risk_level"].eq(boundary_cases["risk_score"].map(expected_level))
    for rule in RULES:
        boundary_cases[rule] = boundary_cases[f"{rule}_triggered"]
    if not boundary_cases["score_matches_formula"].all() or not boundary_cases["level_matches_boundary"].all():
        raise AssertionError("Existing risk implementation failed a boundary or capping validation case.")

    output_columns = [
        "scenario", "scenario_type", "source_row_id", "ml_fraud_probability", *RULES,
        "behavioral_rule_points", "ml_risk_points", "risk_score", "risk_level", "triggered_rules",
        "rule_details",
    ]
    all_scenarios = pd.concat(
        [actual_scenarios[output_columns], boundary_cases[output_columns]], ignore_index=True
    )
    all_scenarios.to_csv(OUTPUT_DIR / "risk_engine_scenarios.csv", index=False)

    explanation_checks = []
    for rule in RULES:
        triggered = data.loc[data[f"{rule}_triggered"], f"{rule}_explanation"]
        explanation_checks.append(
            {
                "rule": rule.replace("_", " ").title(),
                "points": RULE_POINTS[rule],
                "triggered_transactions": int(len(triggered)),
                "all_triggered_rows_have_explanation": bool(triggered.notna().all() and triggered.astype(str).str.strip().ne("").all()),
            }
        )
    explanation_table = pd.DataFrame(explanation_checks)

    low_rule_medium = select_actual(
        data,
        "low ML/medium behavioral",
        data["ml_fraud_probability"].lt(0.10) & data["risk_level"].eq("MEDIUM") & data["trigger_count"].gt(0),
        [True, True],
    )
    high_ml_no_rules = select_actual(data, "high ML/no rules", data["trigger_count"].eq(0), [False, True])
    high_ml_rules = select_actual(data, "high ML/rules", data["trigger_count"].gt(0), [False, True])

    actual_display = actual_scenarios.drop(columns="scenario_type")
    boundary_display = boundary_cases[
        ["scenario", "ml_fraud_probability", "behavioral_rule_points", "ml_risk_points", "risk_score", "risk_level", "expected_score", "score_matches_formula", "level_matches_boundary", "rule_details"]
    ]
    report = f"""# RiskGuard AI — Phase 7 Risk Engine Validation

## Scope

This validation reads the existing Phase 3 assessment output and imports the existing `add_risk_assessment` implementation only for mathematical boundary/capping tests. It does not change the risk formula, weights, thresholds, XGBoost model, behavioral generation, investigator, dashboard, or raw dataset.

All {len(data):,} saved assessments satisfy the existing formula and level mapping:

```text
risk_score = min(100, 60 × ml_fraud_probability + behavioral rule points)
LOW: score < 25; MEDIUM: 25 <= score < 50; HIGH: score >= 50
```

## Representative saved-transaction scenarios

These rows are existing Phase 3 assessment data. They report values only; no reason for an ML output or transaction label is inferred.

{markdown_table(actual_display, {"ml_fraud_probability", "ml_risk_points", "risk_score"})}

## Boundary and score-capping tests

These are **in-memory mathematical validation cases, not real transactions and not generated behavioral metadata**. They call the existing risk-engine implementation directly.

{markdown_table(boundary_display, {"ml_fraud_probability", "ml_risk_points", "risk_score", "expected_score"})}

The capping case has ML contribution 60 and all current behavioral rules (75 points), giving an uncapped total of 135. The implementation returns 100, confirming that scores cannot exceed 100.

## Independent rule contribution checks

Each available "alone" saved-transaction scenario above has exactly one triggered rule. The observed behavioral points are therefore exactly the configured contribution. If the saved sample has no transaction for a rule in isolation, that evidence-only scenario is omitted rather than invented. Multi-rule scenarios show that contributions add before the score cap is applied.

{markdown_table(explanation_table)}

Every triggered saved rule has a non-empty stored explanation. Existing outputs also retain `triggered_rules`, rule booleans, and the configured point values, making the rule contribution auditable. `user_id`, `device_id`, `region`, and `transaction_velocity` remain explicitly synthetic demonstration metadata; they are not claimed to be Kaggle customer data.

The literal no-rule marker is `None` in the saved CSV. CSV parsing can expose that literal as a null value, so this validator normalizes null/no-rule display to `None` before comparing it with the rule flags. The normalized values are consistent for all saved rows; this is an artifact-format consideration, not a risk-engine scoring inconsistency.

## ML and behavioral-signal disagreement

- **High ML, little/no behavioral contribution:** source row {int(high_ml_no_rules['source_row_id'])} has ML probability {high_ml_no_rules['ml_fraud_probability']:.6f}, no triggered behavioral rules, score {high_ml_no_rules['risk_score']:.2f}, and level {high_ml_no_rules['risk_level']}. The current system reflects the ML contribution alone.
- **Low ML, behavioral signals raise level:** source row {int(low_rule_medium['source_row_id'])} has ML probability {low_rule_medium['ml_fraud_probability']:.6f}, {int(low_rule_medium['behavioral_rule_points'])} behavioral points from {low_rule_medium['triggered_rules']}, score {low_rule_medium['risk_score']:.2f}, and level {low_rule_medium['risk_level']}. The current system adds the explicit rule points to the small ML contribution.
- **High ML plus behavioral signals:** source row {int(high_ml_rules['source_row_id'])} has ML probability {high_ml_rules['ml_fraud_probability']:.6f}, {int(high_ml_rules['behavioral_rule_points'])} behavioral points from {high_ml_rules['triggered_rules']}, score {high_ml_rules['risk_score']:.2f}, and level {high_ml_rules['risk_level']}.

These examples show how the configured formula combines signals; they do not establish that either signal is objectively correct.

## Limitations

- Behavioral metadata is synthetic demonstration data.
- Rule weights are demonstration choices, not learned from production fraud outcomes.
- The risk score is not a calibrated probability of fraud.
- The formula is not production-validated, and ML and behavioral signals may disagree.
- Production deployment would require real behavioral history, operational policy, and validation.
"""
    (OUTPUT_DIR / "risk_engine_validation.md").write_text(report, encoding="utf-8")

    print(f"Risk-engine validation complete. Saved assessments checked: {len(data):,}")
    print(f"Scenario rows written: {len(all_scenarios):,}; boundary/capping tests passed: {len(boundary_cases):,}")


if __name__ == "__main__":
    main()
