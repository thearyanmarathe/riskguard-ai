"""Generate the Phase 3 synthetic behavioral-context demonstration.

Run from the project root:
    .venv\\Scripts\\python scripts\\run_behavioral_demo.py

This script reads the Kaggle CSV without modifying it. Synthetic fields are
clearly labelled in every output and are not passed to the Phase 2 ML model.
"""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
from xgboost import XGBClassifier

from behavioral_context import (
    AMOUNT_DEVIATION_THRESHOLD,
    add_risk_assessment,
    add_synthetic_context,
    apply_behavioral_rules,
    methodology,
    rule_counts,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "raw" / "creditcard.csv"
MODEL_ARTIFACT = PROJECT_ROOT / "reports" / "model" / "xgboost_baseline.json"
OUTPUT_DIR = PROJECT_ROOT / "reports" / "behavioral"
RANDOM_SEED = 42
SUBSET_SIZE = 5_000
VELOCITY_THRESHOLD = 6
ML_FEATURE_COLUMNS = ["Time", *[f"V{number}" for number in range(1, 29)], "Amount"]


def main() -> None:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    raw_data = pd.read_csv(DATA_PATH)
    # source_row_id preserves traceability to the immutable CSV row position.
    subset = raw_data.sample(n=SUBSET_SIZE, random_state=RANDOM_SEED).sort_index().copy()
    subset.insert(0, "source_row_id", subset.index)
    subset = subset.reset_index(drop=True)
    amount_threshold = float(subset["Amount"].quantile(0.99))

    enriched = add_synthetic_context(subset, RANDOM_SEED)
    assessed = apply_behavioral_rules(enriched, amount_threshold, VELOCITY_THRESHOLD)

    if not MODEL_ARTIFACT.exists():
        raise FileNotFoundError(
            f"XGBoost artifact not found: {MODEL_ARTIFACT}. "
            "Run scripts/train_baselines.py first to reproduce and save the Phase 2 baseline."
        )
    # The artifact was trained in Phase 2 on exactly these real Kaggle columns.
    # Synthetic demo metadata is explicitly excluded from ML prediction.
    xgboost = XGBClassifier()
    xgboost.load_model(MODEL_ARTIFACT)
    ml_probability = pd.Series(xgboost.predict_proba(assessed[ML_FEATURE_COLUMNS])[:, 1], index=assessed.index)
    ml_status = "available: saved Phase 2 XGBoost baseline scored real Kaggle feature columns only"
    assessed = add_risk_assessment(assessed, ml_probability)

    counts = rule_counts(assessed)
    deviation_summary = assessed["amount_deviation"].describe(percentiles=[0.50, 0.90, 0.95, 0.99]).to_dict()
    output_columns = [
        "source_row_id", "Time", "Amount", "Class", "user_id", "device_id", "region", "transaction_velocity",
        "historical_average_amount", "amount_deviation",
        "ml_fraud_probability", "ml_signal_available", "high_transaction_velocity_triggered",
        "unusual_device_triggered", "unusual_region_triggered", "high_transaction_amount_triggered", "high_amount_deviation_triggered",
        "high_transaction_velocity_explanation", "unusual_device_explanation", "unusual_region_explanation",
        "high_transaction_amount_explanation", "high_amount_deviation_explanation",
        "behavioral_rule_points", "ml_risk_points", "risk_score", "risk_level", "triggered_rules", "risk_explanation",
    ]
    assessed.loc[:, output_columns].to_csv(OUTPUT_DIR / "behavioral_risk_assessments.csv", index=False)
    # Keep every real Kaggle field in this small sample so the enrichment is
    # visibly layered on top of, rather than substituted for, source data.
    assessed.head(25).to_csv(OUTPUT_DIR / "sample_enriched_transactions.csv", index=False)
    metadata = {
        "source": "data/raw/creditcard.csv",
        "raw_columns": ["Time", *[f"V{number}" for number in range(1, 29)], "Amount", "Class"],
        "synthetic_demo_columns": [
            "user_id", "device_id", "region", "transaction_velocity",
            "historical_average_amount", "amount_deviation",
        ],
        "random_seed": RANDOM_SEED,
        "transactions_enriched": len(assessed),
        "ml_signal": ml_status,
        "ml_probability_summary": {
            "minimum": float(assessed["ml_fraud_probability"].min()),
            "maximum": float(assessed["ml_fraud_probability"].max()),
            "mean": float(assessed["ml_fraud_probability"].mean()),
            "median": float(assessed["ml_fraud_probability"].median()),
            "transactions_scored": int(assessed["ml_fraud_probability"].notna().sum()),
        },
        "amount_deviation_summary": {
            "median": float(deviation_summary["50%"]),
            "p90": float(deviation_summary["90%"]),
            "p95": float(deviation_summary["95%"]),
            "p99": float(deviation_summary["99%"]),
            "maximum": float(deviation_summary["max"]),
            "threshold": AMOUNT_DEVIATION_THRESHOLD,
            "triggered_count": counts["high_amount_deviation"],
        },
        "rule_trigger_counts": counts,
        **methodology(amount_threshold, VELOCITY_THRESHOLD),
    }
    (OUTPUT_DIR / "methodology.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    examples = assessed.sort_values(["risk_score", "Amount"], ascending=False).head(3)
    example_rows = "\n".join(
        f"| {row.source_row_id} | {row.Amount:.2f} | {row.ml_fraud_probability:.6f} | {row.behavioral_rule_points:.0f} | {row.risk_score:.2f} | {row.risk_level} | {row.triggered_rules} |"
        for row in examples.itertuples()
    )
    report = f"""# RiskGuard AI — Phase 3: Synthetic Behavioral Context and Rule Engine

## Data separation

- **Real Kaggle fields:** `Time`, `V1`–`V28`, `Amount`, and `Class`. These are read from `data/raw/creditcard.csv` without modification.
- **Synthetic demo fields:** `user_id`, `device_id`, `region`, `transaction_velocity`, `historical_average_amount`, and `amount_deviation`. They are deterministic fabricated metadata for this classroom/demo layer; they do not come from Kaggle and are not ML model inputs.

## Synthetic methodology

A deterministic random subset of {len(assessed):,} Kaggle transactions was selected with seed {RANDOM_SEED}. Synthetic users have a deterministic usual device and usual region; 12% of generated device assignments and 10% of generated region assignments are deliberately different, enabling rule-engine demonstrations. `transaction_velocity` is a synthetic Poisson-generated count in a hypothetical recent window, not real customer behavior. `historical_average_amount` is a seeded, user-level synthetic baseline generated independently of `Amount` and `Class`; it is not real customer history. `amount_deviation = Amount / historical_average_amount`, with safe handling for near-zero baselines. In the generated distribution, the median was {deviation_summary['50%']:.3f}, the 90th percentile {deviation_summary['90%']:.3f}, the 95th percentile {deviation_summary['95%']:.3f}, the 99th percentile {deviation_summary['99%']:.3f}, and the maximum {deviation_summary['max']:.3f}. The fixed demonstration threshold of {AMOUNT_DEVIATION_THRESHOLD:.1f} triggers {counts['high_amount_deviation']:,} transactions ({counts['high_amount_deviation'] / len(assessed):.2%}); it was selected after inspecting this distribution and is not learned from production outcomes.

## ML signal status

`{ml_status}`. `ml_fraud_probability` is the saved Phase 2 XGBoost baseline's probability using only the real Kaggle transaction feature columns (`Time`, `V1`–`V28`, and `Amount`). Synthetic fields are not model inputs and are not claimed to improve the ML baseline.

Across the 5,000 scored transactions, ML probability is minimum {assessed["ml_fraud_probability"].min():.12f}, maximum {assessed["ml_fraud_probability"].max():.12f}, mean {assessed["ml_fraud_probability"].mean():.12f}, and median {assessed["ml_fraud_probability"].median():.12f}.

## Rules

| Rule | Trigger condition | Points | Triggered transactions |
| --- | --- | ---: | ---: |
| High transaction velocity | Synthetic velocity >= {VELOCITY_THRESHOLD} | 20 | {counts['high_transaction_velocity']:,} |
| Unusual device | Synthetic device differs from the user's synthetic usual device | 20 | {counts['unusual_device']:,} |
| Unusual region | Synthetic region differs from the user's synthetic usual region | 15 | {counts['unusual_region']:,} |
| High transaction amount | Real `Amount` >= subset 99th percentile ({amount_threshold:.2f}) | 20 | {counts['high_transaction_amount']:,} |
| High amount deviation | `Amount / historical_average_amount` >= {AMOUNT_DEVIATION_THRESHOLD:.1f} | 20 | {counts['high_amount_deviation']:,} |

Each rule produces a boolean trigger and a short explanation. The assessment output includes all five trigger and explanation columns, plus the combined triggered-rule names and risk explanation. The amount-deviation rule is a demonstration heuristic, not a production-learned rule.

## Risk assessment

`risk_score = min(100, 60 × ml_fraud_probability + behavioral rule points)`.

Rule points are 20 (velocity), 20 (device), 15 (region), 20 (amount), and 20 (amount deviation). Risk levels are **LOW** below 25, **MEDIUM** from 25 to below 50, and **HIGH** at 50 or greater. This is a transparent demonstration formula, not a production-validated financial risk score.

## Example assessments

| Source row | Amount | ML probability | Rule points | Risk score | Risk level | Triggered rules |
| ---: | ---: | ---: | ---: | ---: | --- | --- |
{example_rows}

## Outputs

- `sample_enriched_transactions.csv` — first 25 enriched transactions.
- `behavioral_risk_assessments.csv` — all {len(assessed):,} assessed subset rows with real reference fields and synthetic/demo fields.
- `methodology.json` — fixed seed, field separation, thresholds, and rule counts.
"""
    (OUTPUT_DIR / "behavioral_report.md").write_text(report, encoding="utf-8")

    print(f"Phase 3 complete. Enriched transactions: {len(assessed):,}")
    print("Rule triggers: " + ", ".join(f"{rule}={count:,}" for rule, count in counts.items()))
    print(f"ML signal: {ml_status}")


if __name__ == "__main__":
    main()
