"""Explain the saved Phase 2 XGBoost model without fitting or changing it.

Run from the project root:
    .venv\\Scripts\\python scripts\\explain_model.py

The script reads the raw Kaggle CSV and the saved XGBoost artifact. It uses
only Time, V1-V28, and Amount as model inputs. Native XGBoost prediction
contributions are reported in raw-margin (log-odds) space.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from xgboost import DMatrix, XGBClassifier


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "raw" / "creditcard.csv"
MODEL_PATH = PROJECT_ROOT / "reports" / "model" / "xgboost_baseline.json"
ASSESSMENT_PATH = PROJECT_ROOT / "reports" / "behavioral" / "behavioral_risk_assessments.csv"
OUTPUT_DIR = PROJECT_ROOT / "reports" / "model" / "explainability"
FEATURE_COLUMNS = ["Time", *[f"V{number}" for number in range(1, 29)], "Amount"]
SELECTED_ROWS = {"LOW": 28727, "MEDIUM": 233005, "HIGH": 215984}
TOP_N = 5


def sigmoid(value: np.ndarray) -> np.ndarray:
    """Convert model margin to probability without changing model output."""
    return 1.0 / (1.0 + np.exp(-value))


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


def contribution_details(model: XGBClassifier, features: pd.DataFrame) -> tuple[np.ndarray, np.ndarray]:
    """Return feature margins and bias from native XGBoost contributions."""
    raw = model.get_booster().predict(
        DMatrix(features, feature_names=FEATURE_COLUMNS), pred_contribs=True, strict_shape=True
    )
    # xgboost >= 3 returns (rows, groups, features + bias) for strict_shape.
    raw = np.asarray(raw)
    if raw.ndim == 3:
        raw = raw[:, 0, :]
    if raw.shape != (len(features), len(FEATURE_COLUMNS) + 1):
        raise ValueError(f"Unexpected contribution shape: {raw.shape}")
    return raw[:, :-1], raw[:, -1]


def main() -> None:
    for path, label in ((DATA_PATH, "raw dataset"), (MODEL_PATH, "XGBoost artifact")):
        if not path.exists():
            raise FileNotFoundError(f"{label} not found: {path}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    raw = pd.read_csv(DATA_PATH)
    missing = set(FEATURE_COLUMNS + ["Class"]).difference(raw.columns)
    if missing:
        raise ValueError("Raw CSV is missing required columns: " + ", ".join(sorted(missing)))

    model = XGBClassifier()
    model.load_model(MODEL_PATH)
    artifact_features = list(model.get_booster().feature_names or [])
    if artifact_features != FEATURE_COLUMNS:
        raise ValueError(f"Artifact features differ from Phase 2 features: {artifact_features}")

    selected_ids = list(SELECTED_ROWS.values())
    selected = raw.iloc[selected_ids].copy()
    selected.insert(0, "source_row", selected.index)
    features = selected[FEATURE_COLUMNS]

    # Two predictions around explanation establish that the read-only process
    # did not alter model output. No fit, retraining, or tuning is performed.
    probabilities_before = model.predict_proba(features)[:, 1]
    feature_margins, bias = contribution_details(model, features)
    probabilities_after = model.predict_proba(features)[:, 1]
    prediction_delta = np.abs(probabilities_before - probabilities_after)
    reconstructed_probability = sigmoid(feature_margins.sum(axis=1) + bias)
    reconstruction_delta = np.abs(probabilities_before - reconstructed_probability)
    if not np.allclose(probabilities_before, probabilities_after, rtol=0, atol=1e-12):
        raise AssertionError("Model predictions changed during explainability processing.")
    if not np.allclose(probabilities_before, reconstructed_probability, rtol=0, atol=1e-6):
        raise AssertionError("Native contribution sum does not reconstruct model probability.")

    assessment = pd.DataFrame()
    if ASSESSMENT_PATH.exists():
        assessment = pd.read_csv(ASSESSMENT_PATH)
        assessment["source_row_id"] = assessment["source_row_id"].astype(int)
        assessment = assessment.loc[assessment["source_row_id"].isin(selected_ids)]

    global_gain = model.get_booster().get_score(importance_type="gain")
    importance = pd.DataFrame(
        {
            "feature": FEATURE_COLUMNS,
            "gain": [float(global_gain.get(feature, 0.0)) for feature in FEATURE_COLUMNS],
        }
    ).sort_values(["gain", "feature"], ascending=[False, True], ignore_index=True)
    importance["gain_share_percent"] = importance["gain"] / importance["gain"].sum() * 100
    importance["global_rank"] = np.arange(1, len(importance) + 1)
    importance = importance[["global_rank", "feature", "gain", "gain_share_percent"]]
    importance.to_csv(OUTPUT_DIR / "global_feature_importance.csv", index=False)

    rows = []
    example_summaries = []
    for position, (risk_level, source_row) in enumerate(SELECTED_ROWS.items()):
        contributions = pd.DataFrame(
            {
                "risk_level": risk_level,
                "source_row": source_row,
                "feature": FEATURE_COLUMNS,
                "feature_value": features.iloc[position].to_numpy(),
                "contribution_margin": feature_margins[position],
            }
        )
        contributions["direction"] = np.where(
            contributions["contribution_margin"] >= 0,
            "positive: pushes toward fraud class",
            "negative: pushes away from fraud class",
        )
        contributions["absolute_contribution"] = contributions["contribution_margin"].abs()
        contributions["absolute_rank"] = contributions["absolute_contribution"].rank(method="first", ascending=False).astype(int)
        rows.append(contributions)

        positives = contributions[contributions["contribution_margin"] > 0].nlargest(TOP_N, "contribution_margin")
        negatives = contributions[contributions["contribution_margin"] < 0].nsmallest(TOP_N, "contribution_margin")
        example = {
            "risk_level": risk_level,
            "source_row": source_row,
            "Time": float(selected.iloc[position]["Time"]),
            "Amount": float(selected.iloc[position]["Amount"]),
            "ml_fraud_probability": float(probabilities_before[position]),
            "prediction_recheck_delta": float(prediction_delta[position]),
            "contribution_probability_reconstruction_delta": float(reconstruction_delta[position]),
            "bias_margin": float(bias[position]),
            "top_positive_contributors": [
                {"feature": row.feature, "contribution_margin": float(row.contribution_margin)}
                for row in positives.itertuples()
            ],
            "top_negative_contributors": [
                {"feature": row.feature, "contribution_margin": float(row.contribution_margin)}
                for row in negatives.itertuples()
            ],
        }
        if not assessment.empty:
            match = assessment.loc[assessment["source_row_id"] == source_row]
            if not match.empty:
                example["existing_risk_score"] = float(match.iloc[0]["risk_score"])
                example["existing_risk_level"] = str(match.iloc[0]["risk_level"])
        example_summaries.append(example)

    contributions_all = pd.concat(rows, ignore_index=True)
    contributions_all.to_csv(OUTPUT_DIR / "individual_feature_contributions.csv", index=False)
    (OUTPUT_DIR / "example_transaction_explanations.json").write_text(
        json.dumps(example_summaries, indent=2), encoding="utf-8"
    )

    top_global = importance.head(TOP_N)
    example_tables = []
    for example in example_summaries:
        positives = pd.DataFrame(example["top_positive_contributors"])
        negatives = pd.DataFrame(example["top_negative_contributors"])
        example_tables.append(
            f"### {example['risk_level']} — source row {example['source_row']}\n\n"
            f"Time: {example['Time']:.2f}; Amount: {example['Amount']:.2f}; "
            f"ML fraud probability: {example['ml_fraud_probability']:.8f}.\n\n"
            f"Top positive contributors (toward fraud class):\n\n"
            f"{markdown_table(positives, {'contribution_margin'}) if not positives.empty else 'None'}\n\n"
            f"Top negative contributors (away from fraud class):\n\n"
            f"{markdown_table(negatives, {'contribution_margin'}) if not negatives.empty else 'None'}"
        )

    report = f"""# RiskGuard AI — Phase 8 Model Explainability

## Scope and method

This analysis loads `{MODEL_PATH.relative_to(PROJECT_ROOT).as_posix()}` without fitting, retraining, tuning, or replacing it. It reproduces the Phase 2 model input contract exactly: `Time`, `V1`–`V28`, and `Amount`. Synthetic behavioral fields are not read as model features.

Global importance uses XGBoost's native **gain** importance: the average gain from splits using each feature, as provided by `get_score(importance_type="gain")`. Importance is a model statistic, not causation.

Individual explanations use XGBoost's native `pred_contribs=True` mechanism. Contributions are in raw-margin/log-odds space and sum with the bias term to the model margin. A positive contribution pushes the model toward the fraud class; a negative contribution pushes it away. These are model explanations and do not establish that a feature caused fraud.

## Global feature importance

{markdown_table(top_global, {'gain', 'gain_share_percent'})}

The complete ranked table is in `global_feature_importance.csv`. `V14` is the most important feature by gain in this artifact, followed by `V10`, `V4`, `V8`, and `V12`. The V features are anonymized/transformed; no real-world meaning is assigned to them.

## Individual transaction explanations

The requested demonstrated source rows were all available. LOW/MEDIUM/HIGH labels below are the existing Phase 3 risk-engine labels; this explainability layer does not calculate or alter risk scores.

{chr(10).join(example_tables)}

Full feature-level contributions for all 30 features per example are in `individual_feature_contributions.csv`, and structured summaries are in `example_transaction_explanations.json`.

## Global versus individual importance

The globally highest-gain feature, `V14`, is the top positive contributor for all three selected examples. `V10` is globally second and is a strong negative contributor for LOW and MEDIUM but a strong positive contributor for HIGH. `V4` is also globally important and appears among the strongest positive contributors for MEDIUM and HIGH. This shows that global and individual importance can overlap without being identical; the comparison is descriptive, not causal.

## Prediction and separation checks

- The saved artifact loaded successfully with 30 expected features.
- Predictions before and after contribution calculation were unchanged; maximum probability delta was {prediction_delta.max():.3e}.
- Native contribution sums reconstructed model probabilities within {reconstruction_delta.max():.3e} absolute error.
- No training, fitting, thresholding, risk-engine, behavioral-rule, investigator, or dashboard code was invoked or modified.
- `data/raw/creditcard.csv` was read only.

## Limitations

- `V1`–`V28` are anonymized/transformed features, so real-world meanings must not be invented.
- Feature contribution is a model explanation, not a causal explanation.
- XGBoost feature importance can differ by importance method; this report uses gain.
- An explanation does not prove fraud.
- The model remains a baseline and is not a production-validated fraud system.
"""
    (OUTPUT_DIR / "explainability_methodology.md").write_text(report, encoding="utf-8")

    print(f"Explainability complete. Model features: {len(FEATURE_COLUMNS)}; examples: {len(example_summaries)}")
    print(f"Top gain feature: {importance.iloc[0]['feature']} ({importance.iloc[0]['gain']:.6f})")
    print(f"Maximum prediction recheck delta: {prediction_delta.max():.3e}")
    print(f"Maximum contribution reconstruction delta: {reconstruction_delta.max():.3e}")
    for example in example_summaries:
        print(f"{example['risk_level']}: source row {example['source_row']}, probability {example['ml_fraud_probability']:.8f}")


if __name__ == "__main__":
    main()
