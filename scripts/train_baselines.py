"""Train reproducible Phase 2 fraud-detection baselines.

Run from the project root:
    .venv\\Scripts\\python scripts\\train_baselines.py

The raw CSV is read only. Exact duplicates are removed only from the in-memory
training dataset, before the train/test split, to prevent duplicate-record
leakage between the two sets.
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
import numpy as np
import pandas as pd
import seaborn as sns
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    ConfusionMatrixDisplay,
    average_precision_score,
    confusion_matrix,
    f1_score,
    precision_recall_curve,
    precision_score,
    recall_score,
)
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from xgboost import XGBClassifier


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "raw" / "creditcard.csv"
OUTPUT_DIR = PROJECT_ROOT / "reports" / "model"
XGBOOST_ARTIFACT_PATH = OUTPUT_DIR / "xgboost_baseline.json"
RANDOM_SEED = 42
TEST_SIZE = 0.20


def evaluate_model(name: str, model: object, x_test: pd.DataFrame, y_test: pd.Series) -> tuple[dict, np.ndarray, np.ndarray]:
    """Calculate threshold-based metrics and probability-based average precision."""
    predictions = model.predict(x_test)
    probabilities = model.predict_proba(x_test)[:, 1]
    matrix = confusion_matrix(y_test, predictions, labels=[0, 1])
    metrics = {
        "precision": float(precision_score(y_test, predictions, zero_division=0)),
        "recall": float(recall_score(y_test, predictions, zero_division=0)),
        "f1_score": float(f1_score(y_test, predictions, zero_division=0)),
        "average_precision": float(average_precision_score(y_test, probabilities)),
        "confusion_matrix": matrix.tolist(),
    }
    print(
        f"{name}: precision={metrics['precision']:.6f}, recall={metrics['recall']:.6f}, "
        f"f1={metrics['f1_score']:.6f}, average_precision={metrics['average_precision']:.6f}"
    )
    return metrics, probabilities, matrix


def save_confusion_matrix(name: str, matrix: np.ndarray) -> None:
    """Save a labelled confusion-matrix figure."""
    figure, axis = plt.subplots(figsize=(6, 5))
    ConfusionMatrixDisplay(matrix, display_labels=["Legitimate", "Fraudulent"]).plot(
        ax=axis, cmap="Blues", colorbar=False
    )
    axis.set_title(f"{name} Confusion Matrix (Test Set)")
    figure.tight_layout()
    figure.savefig(OUTPUT_DIR / f"{name.lower().replace(' ', '_')}_confusion_matrix.png", dpi=150)
    plt.close(figure)


def save_precision_recall_plot(y_test: pd.Series, model_probabilities: dict[str, np.ndarray]) -> None:
    """Save PR curves for the two models on the same untouched test set."""
    figure, axis = plt.subplots(figsize=(7, 5))
    for name, probabilities in model_probabilities.items():
        precision, recall, _ = precision_recall_curve(y_test, probabilities)
        average_precision = average_precision_score(y_test, probabilities)
        axis.plot(recall, precision, label=f"{name} (AP={average_precision:.3f})")
    fraud_rate = y_test.mean()
    axis.axhline(fraud_rate, color="gray", linestyle="--", label=f"Fraud rate ({fraud_rate:.3%})")
    axis.set_title("Precision-Recall Curves (Test Set)")
    axis.set_xlabel("Recall")
    axis.set_ylabel("Precision")
    axis.legend()
    figure.tight_layout()
    figure.savefig(OUTPUT_DIR / "precision_recall_comparison.png", dpi=150)
    plt.close(figure)


def duplicate_summary(data: pd.DataFrame) -> dict:
    """Summarize rows pandas identifies as repeats of an earlier exact row."""
    duplicate_rows = data.loc[data.duplicated(keep="first")]
    class_counts = duplicate_rows["Class"].value_counts().reindex([0, 1], fill_value=0)
    total = len(duplicate_rows)
    return {
        "duplicate_rows": total,
        "duplicate_rows_class_0": int(class_counts[0]),
        "duplicate_rows_class_1": int(class_counts[1]),
        "duplicate_rows_class_0_proportion": float(class_counts[0] / total) if total else 0.0,
        "duplicate_rows_class_1_proportion": float(class_counts[1] / total) if total else 0.0,
        "rows_in_duplicate_groups": int(data.duplicated(keep=False).sum()),
        "unique_rows_after_deduplication": int(len(data.drop_duplicates())),
    }


def format_metrics_row(name: str, metrics: dict) -> str:
    return (
        f"| {name} | {metrics['precision']:.6f} | {metrics['recall']:.6f} | "
        f"{metrics['f1_score']:.6f} | {metrics['average_precision']:.6f} |"
    )


def main() -> None:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid")
    raw_data = pd.read_csv(DATA_PATH)
    duplicates = duplicate_summary(raw_data)

    # This derived dataframe exists only in memory; data/raw/creditcard.csv is not changed.
    data = raw_data.drop_duplicates().copy()
    x = data.drop(columns="Class")
    y = data["Class"]
    x_train, x_test, y_train, y_test = train_test_split(
        x, y, test_size=TEST_SIZE, stratify=y, random_state=RANDOM_SEED
    )

    logistic_regression = Pipeline(
        steps=[
            ("scaler", StandardScaler()),
            (
                "model",
                LogisticRegression(
                    class_weight="balanced", max_iter=1000, random_state=RANDOM_SEED, solver="lbfgs"
                ),
            ),
        ]
    )
    logistic_regression.fit(x_train, y_train)
    logistic_metrics, logistic_probabilities, logistic_matrix = evaluate_model(
        "Logistic Regression", logistic_regression, x_test, y_test
    )

    # The weight is computed from training data only, preserving test-set isolation.
    scale_pos_weight = float((y_train == 0).sum() / (y_train == 1).sum())
    xgboost = XGBClassifier(
        n_estimators=300,
        max_depth=4,
        learning_rate=0.1,
        subsample=0.8,
        colsample_bytree=0.8,
        scale_pos_weight=scale_pos_weight,
        eval_metric="logloss",
        random_state=RANDOM_SEED,
        n_jobs=-1,
        tree_method="hist",
    )
    xgboost.fit(x_train, y_train)
    xgboost_metrics, xgboost_probabilities, xgboost_matrix = evaluate_model(
        "XGBoost", xgboost, x_test, y_test
    )
    # Persist the evaluated Phase 2 baseline so later demo layers can score
    # real Kaggle feature rows without retraining or using synthetic metadata.
    xgboost.save_model(XGBOOST_ARTIFACT_PATH)

    save_confusion_matrix("Logistic Regression", logistic_matrix)
    save_confusion_matrix("XGBoost", xgboost_matrix)
    save_precision_recall_plot(
        y_test, {"Logistic Regression": logistic_probabilities, "XGBoost": xgboost_probabilities}
    )

    results = {
        "data_source": "data/raw/creditcard.csv",
        "raw_data_shape": [int(raw_data.shape[0]), int(raw_data.shape[1])],
        "duplicate_analysis": duplicates,
        "deduplication": {
            "applied_to": "in-memory training dataframe only",
            "reason": "Avoid exact duplicate records appearing in both training and test sets.",
        },
        "split": {
            "random_seed": RANDOM_SEED,
            "test_size_proportion": TEST_SIZE,
            "train_rows": int(len(x_train)),
            "test_rows": int(len(x_test)),
            "train_class_counts": {str(key): int(value) for key, value in y_train.value_counts().sort_index().items()},
            "test_class_counts": {str(key): int(value) for key, value in y_test.value_counts().sort_index().items()},
        },
        "logistic_regression": {"class_weight": "balanced", **logistic_metrics},
        "xgboost": {"scale_pos_weight": scale_pos_weight, **xgboost_metrics},
        "xgboost_artifact": str(XGBOOST_ARTIFACT_PATH.relative_to(PROJECT_ROOT).as_posix()),
    }
    (OUTPUT_DIR / "metrics.json").write_text(json.dumps(results, indent=2), encoding="utf-8")

    better_model = "XGBoost" if xgboost_metrics["average_precision"] > logistic_metrics["average_precision"] else "Logistic Regression"
    report = f"""# RiskGuard AI — Phase 2 Baseline Classifiers

Source dataset: `data/raw/creditcard.csv`  
The raw CSV was read only. No data was written to `data/raw/`.

## Duplicate investigation

`pandas.DataFrame.duplicated(keep="first")` identifies **{duplicates['duplicate_rows']:,} duplicate rows**: records identical to an earlier row.

| Duplicate class | Rows | Proportion of duplicate rows |
| --- | ---: | ---: |
| Legitimate (`Class == 0`) | {duplicates['duplicate_rows_class_0']:,} | {duplicates['duplicate_rows_class_0_proportion']:.4%} |
| Fraudulent (`Class == 1`) | {duplicates['duplicate_rows_class_1']:,} | {duplicates['duplicate_rows_class_1_proportion']:.4%} |

There are {duplicates['rows_in_duplicate_groups']:,} rows when counting both original and repeated members of duplicate groups. Exact duplicates were removed **only in memory before splitting**, leaving {len(data):,} unique records. This avoids the same record leaking into both training and test data, which can inflate evaluation results. The raw dataset remains unchanged.

## Reproducible split

- Random seed: {RANDOM_SEED}
- Stratified split: {1 - TEST_SIZE:.0%} train / {TEST_SIZE:.0%} test after in-memory deduplication
- Train rows: {len(x_train):,} — legitimate: {(y_train == 0).sum():,}; fraudulent: {(y_train == 1).sum():,}
- Test rows: {len(x_test):,} — legitimate: {(y_test == 0).sum():,}; fraudulent: {(y_test == 1).sum():,}

Scaling is fitted by the Logistic Regression pipeline on training data only. The test set is used only for final evaluation.

## Evaluation on the untouched test set

| Model | Precision | Recall | F1-score | PR-AUC / Average Precision |
| --- | ---: | ---: | ---: | ---: |
{format_metrics_row('Logistic Regression', logistic_metrics)}
{format_metrics_row('XGBoost', xgboost_metrics)}

### Logistic Regression confusion matrix

| Actual / predicted | Legitimate | Fraudulent |
| --- | ---: | ---: |
| Legitimate | {logistic_matrix[0, 0]:,} | {logistic_matrix[0, 1]:,} |
| Fraudulent | {logistic_matrix[1, 0]:,} | {logistic_matrix[1, 1]:,} |

### XGBoost confusion matrix

| Actual / predicted | Legitimate | Fraudulent |
| --- | ---: | ---: |
| Legitimate | {xgboost_matrix[0, 0]:,} | {xgboost_matrix[0, 1]:,} |
| Fraudulent | {xgboost_matrix[1, 0]:,} | {xgboost_matrix[1, 1]:,} |

## Comparison and limitations

{better_model} has the higher Average Precision on this split, so it is the stronger baseline for ranking likely fraud cases. Accuracy is not a primary metric here: a model predicting every transaction as legitimate would be about {(y_test == 0).mean():.3%} accurate while detecting no fraud.

The models use their default 0.5 decision threshold for precision, recall, and F1. Threshold selection, calibration, cross-validation, and hyperparameter tuning are intentionally outside this baseline phase.
"""
    (OUTPUT_DIR / "baseline_comparison.md").write_text(report, encoding="utf-8")
    print(f"Completed Phase 2. Results saved to: {OUTPUT_DIR.relative_to(PROJECT_ROOT)}")
    print(f"Duplicate rows: {duplicates['duplicate_rows']:,}; unique rows used: {len(data):,}")
    print(f"Train/test rows: {len(x_train):,}/{len(x_test):,}")


if __name__ == "__main__":
    main()
