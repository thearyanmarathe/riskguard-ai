"""Run the three reproducible RiskGuard AI demonstration scenarios.

This runner selects existing saved assessments and delegates investigation to
the application Investigator. It does not retrain, predict, score, persist,
or call an external AI provider.
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Any

import pandas as pd

from ai_investigator import ApplicationInvestigator


PROJECT_ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = PROJECT_ROOT / "demo" / "scenarios.json"
ASSESSMENT_PATH = PROJECT_ROOT / "reports" / "behavioral" / "behavioral_risk_assessments.csv"
EXPECTED_IDS = ("low_risk", "medium_risk", "high_risk")


def load_manifest() -> list[dict[str, Any]]:
    """Load and validate the small, metadata-only scenario manifest."""
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    scenarios = payload.get("scenarios")
    if payload.get("version") != "1.0" or not isinstance(scenarios, list):
        raise ValueError("Demo manifest must contain version 1.0 and a scenarios list.")
    if tuple(item.get("id") for item in scenarios) != EXPECTED_IDS:
        raise ValueError("Demo manifest must contain low_risk, medium_risk, high_risk in order.")
    if len(scenarios) != 3 or len({item.get("source_row_id") for item in scenarios}) != 3:
        raise ValueError("Demo manifest must contain exactly three distinct scenarios and source rows.")
    required = {
        "id", "name", "source_row_id", "expected_risk_level", "expected_risk_score",
        "expected_ml_probability", "expected_behavioral_points", "expected_triggered_rules",
        "explanation", "provenance",
    }
    for scenario in scenarios:
        if not required.issubset(scenario):
            raise ValueError(f"Scenario {scenario.get('id', '<unknown>')} is missing metadata.")
        if scenario["provenance"] != "REAL_TRANSACTION_WITH_SYNTHETIC_BEHAVIORAL_CONTEXT":
            raise ValueError(f"Scenario {scenario['id']} has an invalid provenance label.")
    return scenarios


def select_scenarios(scenarios: list[dict[str, Any]], selected_id: str | None) -> list[dict[str, Any]]:
    if selected_id is None:
        return scenarios
    selected = [scenario for scenario in scenarios if scenario["id"] == selected_id]
    if not selected:
        raise ValueError(f"Unknown scenario: {selected_id}")
    return selected


def validate_result(scenario: dict[str, Any], report: dict[str, Any]) -> None:
    risk = report["risk_assessment"]
    actual_rules = [rule["rule_name"].lower().replace(" ", "_") for rule in report["triggered_behavioral_rules"]]
    checks = {
        "risk level": risk["risk_level"] == scenario["expected_risk_level"],
        "risk score": math.isclose(risk["risk_score"], scenario["expected_risk_score"], abs_tol=1e-9),
        "ML probability": math.isclose(risk["ml_fraud_probability"], scenario["expected_ml_probability"], abs_tol=1e-9),
        "behavioral points": risk["behavioral_rule_points"] == scenario["expected_behavioral_points"],
        "triggered rules": actual_rules == scenario["expected_triggered_rules"],
        "deterministic fallback": report.get("fallback_used") is True and report.get("provider_used") is False,
    }
    failed = [name for name, passed in checks.items() if not passed]
    if failed:
        raise ValueError(f"Scenario {scenario['id']} validation failed: {', '.join(failed)}")


def run(selected_id: str | None = None) -> list[dict[str, Any]]:
    scenarios = select_scenarios(load_manifest(), selected_id)
    if not ASSESSMENT_PATH.exists():
        raise FileNotFoundError(f"Saved assessment file not found: {ASSESSMENT_PATH}")
    assessments = pd.read_csv(ASSESSMENT_PATH)
    investigator = ApplicationInvestigator(provider_factory=lambda: None)
    results = []
    for scenario in scenarios:
        matches = assessments.loc[assessments["source_row_id"] == scenario["source_row_id"]]
        if len(matches) != 1:
            raise ValueError(f"Expected one saved assessment for source row {scenario['source_row_id']}.")
        report = investigator.investigate(matches.iloc[0].to_dict())
        validate_result(scenario, report)
        results.append({"scenario": scenario, "report": report})
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Run reproducible RiskGuard AI demo scenarios.")
    parser.add_argument("--scenario", choices=EXPECTED_IDS, help="Run one scenario instead of all three.")
    arguments = parser.parse_args()
    try:
        results = run(arguments.scenario)
    except (OSError, ValueError, json.JSONDecodeError) as error:
        print(f"Demo validation: FAILED - {error}")
        return 1

    print("=" * 50)
    print("RiskGuard AI Demo")
    print("=" * 50)
    for index, item in enumerate(results, start=1):
        scenario = item["scenario"]
        report = item["report"]
        risk = report["risk_assessment"]
        print(f"\n[{index}] {risk['risk_level']} RISK")
        print(f"Scenario: {scenario['name']}")
        print(f"Source Row: {scenario['source_row_id']}")
        print(f"ML Probability: {risk['ml_fraud_probability']:.8f}")
        print(f"Behavioral Points: {risk['behavioral_rule_points']:.0f}")
        print(f"Risk Score: {risk['risk_score']:.2f}")
        print(f"Risk Level: {risk['risk_level']}")
        print(f"Why: {scenario['explanation']}")
        print(f"Rules: {scenario['expected_triggered_rules'] or 'none'}")
        if index != len(results):
            print("\n" + "-" * 50)
    print("\n" + "=" * 50)
    print("Demo validation: PASSED")
    print("=" * 50)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
