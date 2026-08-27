"""Analyze existing Phase 3 behavioral outputs without changing them.

Run from the project root:
    .venv\\Scripts\\python scripts\\analyze_behavioral_signals.py

This script reads the saved Phase 3 assessment and metadata. It does not call
the metadata generator, apply rules, create new behavioral fields, or write to
the raw Kaggle dataset.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[1]
BEHAVIORAL_DIR = PROJECT_ROOT / "reports" / "behavioral"
ASSESSMENT_PATH = BEHAVIORAL_DIR / "behavioral_risk_assessments.csv"
METHODOLOGY_PATH = BEHAVIORAL_DIR / "methodology.json"
BEHAVIORAL_REPORT_PATH = BEHAVIORAL_DIR / "behavioral_report.md"
SAMPLE_PATH = BEHAVIORAL_DIR / "sample_enriched_transactions.csv"
OUTPUT_PATH = BEHAVIORAL_DIR / "behavioral_signal_analysis.md"
FREQUENCY_PATH = BEHAVIORAL_DIR / "behavioral_signal_frequency.csv"
RULES = {
    "high_transaction_velocity": "High Transaction Velocity",
    "unusual_device": "Unusual Device",
    "unusual_region": "Unusual Region",
    "high_transaction_amount": "High Transaction Amount",
    "high_amount_deviation": "High Amount Deviation",
}
SYNTHETIC_FIELDS = [
    "user_id", "device_id", "region", "transaction_velocity",
    "historical_average_amount", "amount_deviation",
]


def markdown_table(data: pd.DataFrame, float_columns: set[str] | None = None) -> str:
    float_columns = float_columns or set()
    columns = list(data.columns)
    rows = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---:"] * len(columns)) + " |"]
    for row in data.itertuples(index=False):
        values = []
        for column, value in zip(columns, row):
            if column in float_columns:
                values.append(f"{float(value):.6f}")
            else:
                values.append(str(value).replace("|", "\\|"))
        rows.append("| " + " | ".join(values) + " |")
    return "\n".join(rows)


def rule_list(row: pd.Series) -> str:
    names = [label for rule, label in RULES.items() if bool(row[f"{rule}_triggered"])]
    return "; ".join(names) if names else "None"


def main() -> None:
    for path in (ASSESSMENT_PATH, METHODOLOGY_PATH, BEHAVIORAL_REPORT_PATH, SAMPLE_PATH):
        if not path.exists():
            raise FileNotFoundError(f"Required Phase 3 artifact not found: {path}")

    with METHODOLOGY_PATH.open(encoding="utf-8") as file:
        methodology = json.load(file)
    if methodology.get("synthetic_demo_columns") != SYNTHETIC_FIELDS:
        raise AssertionError("Phase 3 metadata does not identify the expected synthetic fields.")
    if set(methodology.get("raw_columns", [])) != {"Time", *[f"V{i}" for i in range(1, 29)], "Amount", "Class"}:
        raise AssertionError("Phase 3 metadata raw-column provenance is inconsistent.")

    data = pd.read_csv(ASSESSMENT_PATH)
    sample = pd.read_csv(SAMPLE_PATH)
    required = {
        "source_row_id", "Time", "Amount", "Class", "ml_fraud_probability", "behavioral_rule_points",
        "ml_risk_points", "risk_score", "risk_level", *[f"{rule}_triggered" for rule in RULES],
        *[f"{rule}_explanation" for rule in RULES], *SYNTHETIC_FIELDS,
    }
    missing = required.difference(data.columns)
    if missing:
        raise ValueError("Assessment is missing required columns: " + ", ".join(sorted(missing)))
    if not set(SYNTHETIC_FIELDS).issubset(sample.columns):
        raise AssertionError("Sample enriched output is missing synthetic-field labels.")
    if len(data) != int(methodology["transactions_enriched"]):
        raise AssertionError("Assessment row count disagrees with Phase 3 methodology.")

    for rule in RULES:
        data[f"{rule}_triggered"] = data[f"{rule}_triggered"].astype(str).str.lower().eq("true")
    trigger_columns = [f"{rule}_triggered" for rule in RULES]
    data["trigger_count"] = data[trigger_columns].sum(axis=1).astype(int)
    data["derived_triggered_rules"] = data.apply(rule_list, axis=1)
    stored_rules = data["triggered_rules"].fillna("None").astype(str).str.strip()
    if not stored_rules.eq(data["derived_triggered_rules"]).all():
        raise AssertionError("Saved combined rule names disagree with individual rule flags.")

    rule_rows = []
    for rule, label in RULES.items():
        triggered = data[f"{rule}_triggered"]
        rule_rows.append({
            "signal": label,
            "field": rule,
            "points": int(methodology["rule_points"][rule]),
            "triggered_count": int(triggered.sum()),
            "triggered_percent": float(triggered.mean() * 100),
            "explanations_present_when_triggered": bool(
                data.loc[triggered, f"{rule}_explanation"].notna().all()
                and data.loc[triggered, f"{rule}_explanation"].astype(str).str.strip().ne("").all()
            ),
        })
    frequency = pd.DataFrame(rule_rows)
    frequency.to_csv(FREQUENCY_PATH, index=False)

    combination_counts = data["trigger_count"].value_counts().sort_index()
    points_summary = data.groupby("behavioral_rule_points", as_index=False).agg(
        transactions=("source_row_id", "size"),
        mean_risk_score=("risk_score", "mean"),
        minimum_risk_score=("risk_score", "min"),
        maximum_risk_score=("risk_score", "max"),
    )
    points_summary["percent"] = points_summary["transactions"] / len(data) * 100
    level_by_behavior = pd.crosstab(data["behavioral_rule_points"], data["risk_level"]).reindex(columns=["LOW", "MEDIUM", "HIGH"], fill_value=0).reset_index()

    examples = {
        "No behavioral signals": data.loc[data["trigger_count"].eq(0)].sort_values("source_row_id").iloc[0],
        "One behavioral signal": data.loc[data["trigger_count"].eq(1)].sort_values("source_row_id").iloc[0],
        "Multiple behavioral signals": data.loc[data["trigger_count"].ge(2)].sort_values(["trigger_count", "source_row_id"]).iloc[0],
    }
    example_rows = []
    for name, row in examples.items():
        example_rows.append({
            "example": name,
            "source_row_id": int(row["source_row_id"]),
            "ml_fraud_probability": float(row["ml_fraud_probability"]),
            "behavioral_rule_points": int(row["behavioral_rule_points"]),
            "risk_score": float(row["risk_score"]),
            "risk_level": str(row["risk_level"]),
            "triggered_rules": rule_list(row),
        })
    example_table = pd.DataFrame(example_rows)

    most_common_count = int(combination_counts.idxmax())
    multi_count = int(data["trigger_count"].ge(2).sum())
    zero_count = int(data["trigger_count"].eq(0).sum())
    one_count = int(data["trigger_count"].eq(1).sum())
    mean_behavioral = float(data["behavioral_rule_points"].mean())
    mean_risk = float(data["risk_score"].mean())
    behavioral_share = mean_behavioral / mean_risk * 100 if mean_risk else 0.0
    max_points = int(data["behavioral_rule_points"].max())
    max_signal_count = int(data["trigger_count"].max())
    deviation_stats = data["amount_deviation"].describe(percentiles=[0.50, 0.90, 0.95, 0.99])
    combination_table = pd.DataFrame(
        {
            "number_of_triggered_rules": combination_counts.index,
            "transactions": combination_counts.values,
            "percent": combination_counts.values / len(data) * 100,
        }
    )

    report = f"""# RiskGuard AI — Phase 9 Behavioral Signal Analysis

## Scope and provenance

This is a read-only analysis of the existing Phase 3 outputs. It reads `behavioral_risk_assessments.csv`, `sample_enriched_transactions.csv`, `methodology.json`, and `behavioral_report.md`; it does not call the behavioral generator or rule engine and does not create new metadata.

The real Kaggle fields are `Time`, `V1`–`V28`, `Amount`, and `Class`. The fields analyzed here—`user_id`, `device_id`, `region`, `transaction_velocity`, `historical_average_amount`, and `amount_deviation`—are fabricated synthetic demonstration metadata. They do not come from the Kaggle dataset and are not XGBoost inputs.

## Current field generation

- `user_id`: reproducibly assigned as `demo_user_###` from seeded random integers from 1 through 500.
- `device_id`: each synthetic user has a deterministic usual device; 12% of generated assignments are deliberately replaced with a different synthetic device.
- `region`: each synthetic user has a deterministic usual region among North, South, East, West, and Central; 10% of generated assignments are deliberately replaced with a different synthetic region.
- `transaction_velocity`: a seeded Poisson-generated count with lambda 1.8, described as prior transactions in a hypothetical recent window. It is not real customer history.
- `historical_average_amount`: a seeded lognormal user-level synthetic baseline generated independently of `Amount`, `Class`, model predictions, and risk scores. It is not real customer history.
- `amount_deviation`: `Amount / historical_average_amount`, safely handled for near-zero baselines. It is a synthetic demonstration ratio, not a production spending profile.

The Phase 3 subset contains {len(data):,} saved assessments, uses seed {methodology['random_seed']}, and computes the amount rule threshold from the subset at {methodology['amount_threshold']:.2f}. The generated `amount_deviation` distribution has median {deviation_stats['50%']:.3f}, p90 {deviation_stats['90%']:.3f}, p95 {deviation_stats['95%']:.3f}, p99 {deviation_stats['99%']:.3f}, and maximum {deviation_stats['max']:.3f}. The fixed threshold of {methodology['amount_deviation_threshold']:.1f} triggers {int(data['high_amount_deviation_triggered'].sum()):,} rows ({data['high_amount_deviation_triggered'].mean():.2%}), so it is not triggered by almost every transaction; it remains a demonstration choice.

## Current rule behavior and frequencies

Each rule is an independent boolean condition. Points are added when its condition is true; they do not represent learned production fraud evidence.

{markdown_table(frequency, {'triggered_percent'})}

The existing rules trigger as follows: velocity is synthetic velocity >= {methodology['velocity_threshold']}; unusual device means the synthetic device differs from the synthetic user's deterministic usual device; unusual region means the synthetic region differs from the synthetic user's deterministic usual region; high amount means real Kaggle `Amount` is at least the subset 99th percentile; and high amount deviation means `amount_deviation` >= {methodology['amount_deviation_threshold']:.1f}. The high-amount rule directly uses a real Kaggle field; the amount-deviation rule uses that field only in combination with a separate synthetic baseline. Both remain separate from XGBoost features.

## Multiple signals

{markdown_table(combination_table, {'percent'})}

{multi_count:,} transactions ({multi_count / len(data):.2%}) trigger two or more rules. {zero_count:,} ({zero_count / len(data):.2%}) trigger no rules and {one_count:,} ({one_count / len(data):.2%}) trigger exactly one. The most common trigger-count group is {most_common_count} rule(s). The maximum observed is {max_signal_count} simultaneous rules, with {max_points} behavioral points.

## Behavioral points and final risk scores

The existing implementation uses `min(100, 60 × ml_fraud_probability + behavioral_rule_points)`. In these saved outputs, mean behavioral points are {mean_behavioral:.3f}, mean final risk score is {mean_risk:.3f}, and the ratio of those means is {behavioral_share:.2f}%. This ratio is descriptive—not a causal or probability interpretation—and ML scores vary across rows.

{markdown_table(points_summary, {'mean_risk_score', 'minimum_risk_score', 'maximum_risk_score', 'percent'})}

Risk levels by behavioral points alone, while retaining the existing ML contribution, are:

{markdown_table(level_by_behavior, set())}

## Representative existing examples

{markdown_table(example_table, {'ml_fraud_probability', 'risk_score'})}

These are existing saved assessment rows, not newly constructed transactions. The examples show that no rules add zero points, one rule adds its configured 15 or 20 points, and multiple rules add their configured points before the existing cap and level mapping. The new amount-deviation rule contributes 20 points when its demonstration threshold is met.

## Rule review

No current rule is mathematically redundant: the five trigger flags represent different conditions and have distinct behavioral or amount inputs. Three conceptual overlaps are worth documenting:

- Unusual device is a synthetic comparison against a deterministic expected device. It is useful for showing explainable device mismatch, but it is not evidence of real account takeover because there is no real device history.
- Unusual region has the same limitation for location. It is useful as a demonstration of deviation from a synthetic baseline, but it does not establish suspicious geography.
- High amount deviation uses a synthetic user baseline and is distinct from the global high-amount threshold, but both include `Amount`; their overlap should be explained rather than treated as independent evidence.

The high-amount rule is potentially problematic if read as behavioral evidence: it uses real `Amount` and a subset-derived percentile, not transaction history. It is transparent and useful for demonstrating a threshold, but it should not be described as learned fraud behavior. Velocity is also a hypothetical count, not observed history. These are demonstration limitations, not changes to the implementation.

## Candidate richer signals

| Candidate | What it could represent | Data required | Reproducible from current setup? | Demonstration value and risk |
| --- | --- | --- | --- | --- |
| `account_age` | Elapsed time since a synthetic account was opened | Synthetic account creation timestamp and an as-of transaction time | Partly; a seeded synthetic creation date could be generated, but none exists now | Useful for showing account-tenure context. High risk of implying real customer lifecycle data unless explicitly labelled synthetic. |
| `historical_average_amount` | Typical prior transaction amount for a synthetic user | Ordered transaction history and prior amounts per user | Partly; current repeated synthetic users and `Amount` could support a deterministic in-memory history, but that history is not currently stored | Useful baseline for amount context. Must exclude the current transaction and be labelled fabricated history. |
| `amount_deviation` | Difference or ratio between current amount and prior synthetic average | `historical_average_amount`, prior-count rules, and a zero-history policy | Partly; depends on the same synthetic history as above | Likely the most useful companion to historical average because it explains why an amount is unusual for a synthetic user. Can mislead if presented as production spending behavior. |
| `transaction_frequency` | Number or rate of prior transactions in a defined time window | Ordered event times and user history; a clear window definition | Partly; current `Time` is elapsed time and synthetic users repeat, but no real history exists | Potentially useful, but it overlaps strongly with current `transaction_velocity`; adding both could duplicate one concept. |
| `new_device` | Whether a device is first-seen for a synthetic user | Ordered device history by user and a first-seen definition | Partly; current synthetic rows can be ordered by source row, but first-seen history is not an existing field | Useful and more history-oriented than a static mismatch. It can be misleading if the fabricated first-seen sequence is treated as real device telemetry. |
| `location_deviation` | Distance or mismatch from a user's prior synthetic location pattern | Ordered locations plus a baseline or coordinates; current regions are only categorical | Weakly; categorical mismatch is already represented by `unusual_region`; no coordinates or history exist | Low incremental value without richer synthetic geography. Could create false precision or duplicate the existing region rule. |

The most useful candidates for an explicitly labelled demonstration are `historical_average_amount` plus `amount_deviation`, followed by either `new_device` or `transaction_frequency`—but only after defining synthetic history and avoiding duplicate point meanings. The first two are now implemented by the Phase 9 update; the latter candidates remain unimplemented.

Signals I recommend not adding in the next small change are `location_deviation` without coordinates/history, because it would likely duplicate `unusual_region`, and `transaction_frequency` alongside `transaction_velocity` without a distinct time-window definition, because it could be a relabelled duplicate. `account_age` should also wait unless the demonstration needs lifecycle context; it introduces a new synthetic premise with limited connection to the current transaction data.

## Limitations and safeguards

- All six behavioral fields are synthetic demonstration metadata.
- The rule weights and thresholds are demonstration choices, not learned from production fraud outcomes.
- Behavioral association in these outputs does not prove fraud or causation.
- `Amount` is a real Kaggle field, but the high-amount threshold is derived from this demonstration subset.
- Production deployment would require real behavioral history, validated definitions, monitoring, and separate model/rule validation.
- This Phase 9 analysis did not modify existing behavior and did not modify `data/raw/creditcard.csv`.
"""
    OUTPUT_PATH.write_text(report, encoding="utf-8")
    print(f"Behavioral analysis complete. Assessments analyzed: {len(data):,}")
    print(f"Multi-rule transactions: {multi_count:,} ({multi_count / len(data):.2%})")
    print("Rule frequencies: " + ", ".join(f"{row.field}={row.triggered_count:,}" for row in frequency.itertuples()))
    print(f"Report: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
