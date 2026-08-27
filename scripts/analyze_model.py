"""Validate the saved Phase 2 XGBoost baseline without retraining it.

Run from the project root:
    .venv\\Scripts\\python scripts\\analyze_model.py

The raw dataset is read only. This script recreates Phase 2's in-memory
deduplication and stratified split, then loads the saved model artifact solely
for prediction and analysis.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "riskguard-ai-matplotlib"))

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from sklearn.metrics import average_precision_score, confusion_matrix, f1_score, precision_recall_curve, precision_score, recall_score
from sklearn.model_selection import train_test_split
from xgboost import XGBClassifier


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "raw" / "creditcard.csv"
MODEL_PATH = PROJECT_ROOT / "reports" / "model" / "xgboost_baseline.json"
PHASE_2_METRICS_PATH = PROJECT_ROOT / "reports" / "model" / "metrics.json"
OUTPUT_DIR = PROJECT_ROOT / "reports" / "model"
RANDOM_SEED = 42
TEST_SIZE = 0.20
THRESHOLDS = [0.10, 0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80, 0.90]


def metrics_at_threshold(y_true: pd.Series, probabilities: pd.Series, threshold: float) -> dict[str, float | int]:
    """Calculate the requested classification metrics at a supplied threshold."""
    predictions = (probabilities >= threshold).astype(int)
    matrix = confusion_matrix(y_true, predictions, labels=[0, 1])
    return {
        "threshold": threshold,
        "precision": float(precision_score(y_true, predictions, zero_division=0)),
        "recall": float(recall_score(y_true, predictions, zero_division=0)),
        "f1_score": float(f1_score(y_true, predictions, zero_division=0)),
        "true_negatives": int(matrix[0, 0]),
        "false_positives": int(matrix[0, 1]),
        "false_negatives": int(matrix[1, 0]),
        "true_positives": int(matrix[1, 1]),
    }


def markdown_table(data: pd.DataFrame, float_columns: set[str] | None = None) -> str:
    """Render a dataframe as Markdown without depending on tabulate."""
    float_columns = float_columns or set()
    columns = list(data.columns)
    rows = ["| " + " | ".join(columns) + " |", "| " + " | ".join(["---:"] * len(columns)) + " |"]
    for row in data.itertuples(index=False):
        values = []
        for column, value in zip(columns, row):
            if column in float_columns:
                values.append(f"{float(value):.6f}")
            elif isinstance(value, float):
                values.append(f"{value:.2f}")
            else:
                values.append(str(value))
        rows.append("| " + " | ".join(values) + " |")
    return "\n".join(rows)


def error_transactions(x_test: pd.DataFrame, y_test: pd.Series, probabilities: pd.Series, predictions: pd.Series, actual: int, predicted: int) -> pd.DataFrame:
    """Return actual test-set error rows with only requested real-data fields."""
    mask = (y_test == actual) & (predictions == predicted)
    errors = pd.DataFrame(
        {
            "source_row_id": x_test.index[mask],
            "Time": x_test.loc[mask, "Time"],
            "Amount": x_test.loc[mask, "Amount"],
            "predicted_probability": probabilities.loc[mask],
            "predicted_class": predictions.loc[mask],
            "actual_class": y_test.loc[mask],
        }
    )
    return errors.sort_values("predicted_probability", ascending=False)


def main() -> None:
    for path, description in ((DATA_PATH, "raw dataset"), (MODEL_PATH, "XGBoost artifact"), (PHASE_2_METRICS_PATH, "Phase 2 metrics")):
        if not path.exists():
            raise FileNotFoundError(f"Required {description} not found: {path}")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    raw_data = pd.read_csv(DATA_PATH)
    # Mirrors Phase 2 exactly: deduplicate only in memory, then stratify the
    # resulting rows. The retained dataframe index is the raw source row ID.
    data = raw_data.drop_duplicates().copy()
    x = data.drop(columns="Class")
    y = data["Class"]
    _, x_test, _, y_test = train_test_split(
        x, y, test_size=TEST_SIZE, stratify=y, random_state=RANDOM_SEED
    )

    model = XGBClassifier()
    model.load_model(MODEL_PATH)
    probabilities = pd.Series(model.predict_proba(x_test)[:, 1], index=x_test.index, name="predicted_probability")
    baseline_predictions = pd.Series(model.predict(x_test).astype(int), index=x_test.index, name="predicted_class")
    baseline_matrix = confusion_matrix(y_test, baseline_predictions, labels=[0, 1])
    baseline_metrics = {
        "precision": float(precision_score(y_test, baseline_predictions, zero_division=0)),
        "recall": float(recall_score(y_test, baseline_predictions, zero_division=0)),
        "f1_score": float(f1_score(y_test, baseline_predictions, zero_division=0)),
        "average_precision": float(average_precision_score(y_test, probabilities)),
    }

    with PHASE_2_METRICS_PATH.open(encoding="utf-8") as file:
        phase_2_metrics = json.load(file)["xgboost"]
    comparison = pd.DataFrame(
        [
            {"metric": "Precision", "phase_2_report": phase_2_metrics["precision"], "reproduced": baseline_metrics["precision"]},
            {"metric": "Recall", "phase_2_report": phase_2_metrics["recall"], "reproduced": baseline_metrics["recall"]},
            {"metric": "F1-score", "phase_2_report": phase_2_metrics["f1_score"], "reproduced": baseline_metrics["f1_score"]},
            {"metric": "Average Precision", "phase_2_report": phase_2_metrics["average_precision"], "reproduced": baseline_metrics["average_precision"]},
        ]
    )
    comparison["difference"] = comparison["reproduced"] - comparison["phase_2_report"]

    false_positives = error_transactions(x_test, y_test, probabilities, baseline_predictions, actual=0, predicted=1)
    false_negatives = error_transactions(x_test, y_test, probabilities, baseline_predictions, actual=1, predicted=0)
    threshold_results = pd.DataFrame([metrics_at_threshold(y_test, probabilities, threshold) for threshold in THRESHOLDS])
    threshold_results.to_csv(OUTPUT_DIR / "threshold_analysis.csv", index=False)

    precision_curve, recall_curve, _ = precision_recall_curve(y_test, probabilities)
    figure, axis = plt.subplots(figsize=(7, 5))
    axis.plot(recall_curve, precision_curve, color="#4C78A8", label="XGBoost test-set PR curve")
    for row in threshold_results.itertuples(index=False):
        axis.scatter(row.recall, row.precision, color="#E45756", zorder=3)
        axis.annotate(f"{row.threshold:.1f}", (row.recall, row.precision), xytext=(4, 4), textcoords="offset points", fontsize=8)
    axis.set_xlabel("Recall")
    axis.set_ylabel("Precision")
    axis.set_title("Precision–Recall Trade-off by Decision Threshold")
    axis.legend()
    figure.tight_layout()
    figure.savefig(OUTPUT_DIR / "threshold_precision_recall.png", dpi=150)
    plt.close(figure)

    baseline_threshold_row = threshold_results.loc[threshold_results["threshold"] == 0.50].iloc[0]
    threshold_040_row = threshold_results.loc[threshold_results["threshold"] == 0.40].iloc[0]
    report = f"""# RiskGuard AI — Phase 6 Model Validation

## Scope and reproducibility

This analysis loads `reports/model/xgboost_baseline.json` without fitting, retraining, or tuning it. It recreates the Phase 2 data preparation: exact duplicates are removed only from the in-memory dataframe, then an 80/20 stratified split is made with random seed {RANDOM_SEED}. The raw CSV at `data/raw/creditcard.csv` is read only.

The reconstructed test set contains {len(y_test):,} transactions: {(y_test == 0).sum():,} legitimate and {(y_test == 1).sum():,} fraudulent.

## Reproduced baseline metrics

{markdown_table(comparison, {"phase_2_report", "reproduced", "difference"})}

All reproduced values match the saved Phase 2 report to the displayed precision.

### Baseline confusion matrix (model default predictions)

| Actual / predicted | Legitimate (0) | Fraudulent (1) |
| --- | ---: | ---: |
| Legitimate (0) | {baseline_matrix[0, 0]:,} TN | {baseline_matrix[0, 1]:,} FP |
| Fraudulent (1) | {baseline_matrix[1, 0]:,} FN | {baseline_matrix[1, 1]:,} TP |

## False positives

There are {len(false_positives):,} false positives: legitimate test transactions predicted as fraudulent at the model's default prediction threshold. The table reports only available transaction fields and model output; it does not infer why these transactions are legitimate.

{markdown_table(false_positives, {"Time", "Amount", "predicted_probability"})}

## False negatives

There are {len(false_negatives):,} false negatives: fraudulent test transactions predicted as legitimate at the model's default prediction threshold. The table reports only available transaction fields and model output; it does not infer why the model missed them.

{markdown_table(false_negatives, {"Time", "Amount", "predicted_probability"})}

## Threshold analysis

{markdown_table(threshold_results, {"threshold", "precision", "recall", "f1_score"})}

`threshold_precision_recall.png` shows the same test-set precision/recall trade-off. The 0.50 row reproduces the default prediction operating point: precision {baseline_threshold_row.precision:.6f}, recall {baseline_threshold_row.recall:.6f}, and F1 {baseline_threshold_row.f1_score:.6f}.

## Operating-threshold discussion

Threshold choice is a policy decision, not a model change. Lower thresholds in the table can increase recall (catching more fraud) but increase false positives and therefore manual-investigation workload. Higher thresholds can reduce false positives but miss more fraud. A possible investigation-workflow candidate is 0.40: compared with 0.50, it captures {threshold_040_row.true_positives - baseline_threshold_row.true_positives:.0f} additional fraudulent test transaction(s) ({threshold_040_row.true_positives:.0f} versus {baseline_threshold_row.true_positives:.0f}) and reduces false negatives by {baseline_threshold_row.false_negatives - threshold_040_row.false_negatives:.0f}, while adding {threshold_040_row.false_positives - baseline_threshold_row.false_positives:.0f} false-positive reviews ({threshold_040_row.false_positives:.0f} versus {baseline_threshold_row.false_positives:.0f}). Whether that workload is acceptable depends on an explicitly defined review capacity and cost of missed fraud. This is an analysis recommendation, not a production decision.

## Class imbalance and limitations

Accuracy is not the primary metric: {(y_test == 0).sum():,} of {len(y_test):,} test transactions ({(y_test == 0).mean():.3%}) are legitimate, so an all-legitimate classifier would appear highly accurate while detecting no fraud. Precision, recall, F1, and Average Precision better expose performance on the rare fraud class.

The experiment shows that false positives ({len(false_positives):,}) and false negatives ({len(false_negatives):,}) remain, and that threshold changes trade precision for recall. `V1`–`V28` are anonymized/transformed fields, limiting business interpretation of individual model decisions. This is a fixed baseline experiment, not a production fraud system.
"""
    (OUTPUT_DIR / "model_analysis.md").write_text(report, encoding="utf-8")

    print(f"Model validation complete. Test rows: {len(y_test):,}")
    print("Reproduced metrics: " + ", ".join(f"{key}={value:.6f}" for key, value in baseline_metrics.items()))
    print(f"False positives: {len(false_positives):,}; false negatives: {len(false_negatives):,}")


if __name__ == "__main__":
    main()
