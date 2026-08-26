"""Reproducible exploratory data analysis for the RiskGuard AI dataset.

Run from the project root:
    .venv\\Scripts\\python scripts\\eda.py

The script only reads data/raw/creditcard.csv.  It writes a Markdown report and
PNG figures to reports/eda/.
"""

import os
import tempfile
from pathlib import Path

# Keep Matplotlib's cache inside the project instead of relying on a user-level
# directory that may not be writable in automated environments. This cache is
# not an analysis result, so it belongs in the operating system's temp area.
os.environ.setdefault("MPLCONFIGDIR", str(Path(tempfile.gettempdir()) / "riskguard-ai-matplotlib"))

import matplotlib

matplotlib.use("Agg")  # Allow reproducible, non-interactive runs.

import matplotlib.pyplot as plt
import pandas as pd
import seaborn as sns


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = PROJECT_ROOT / "data" / "raw" / "creditcard.csv"
OUTPUT_DIR = PROJECT_ROOT / "reports" / "eda"


def save_class_distribution_plot(class_counts: pd.Series) -> None:
    """Save a bar chart showing the target-class imbalance."""
    plot_data = class_counts.rename(index={0: "Legitimate", 1: "Fraudulent"})
    fig, ax = plt.subplots(figsize=(8, 5))
    sns.barplot(x=plot_data.index, y=plot_data.values, hue=plot_data.index,
                palette=["#4C78A8", "#E45756"], legend=False, ax=ax)
    ax.set_title("Transaction Counts by Class")
    ax.set_xlabel("Transaction class")
    ax.set_ylabel("Number of transactions")
    for index, count in enumerate(plot_data.values):
        ax.text(index, count, f"{count:,}", ha="center", va="bottom")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "class_distribution.png", dpi=150)
    plt.close(fig)


def save_amount_distribution_plot(data: pd.DataFrame) -> None:
    """Save the amount distribution, clipped only for display readability."""
    display_limit = data["Amount"].quantile(0.99)
    fig, ax = plt.subplots(figsize=(10, 5))
    sns.histplot(data=data, x="Amount", bins=60, color="#4C78A8", ax=ax)
    ax.set_xlim(0, display_limit)
    ax.set_title("Transaction Amount Distribution (through 99th percentile)")
    ax.set_xlabel("Amount")
    ax.set_ylabel("Number of transactions")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "amount_distribution.png", dpi=150)
    plt.close(fig)


def save_time_by_class_plot(data: pd.DataFrame) -> None:
    """Save transaction counts over time for each class."""
    hourly_counts = (
        data.assign(Hour=(data["Time"] / 3600).astype(int))
        .groupby(["Hour", "Class"], observed=True)
        .size()
        .unstack(fill_value=0)
        .rename(columns={0: "Legitimate", 1: "Fraudulent"})
    )
    fig, ax = plt.subplots(figsize=(10, 5))
    hourly_counts.plot(kind="line", marker="o", ax=ax, color=["#4C78A8", "#E45756"])
    ax.set_title("Transactions by Elapsed Hour and Class")
    ax.set_xlabel("Elapsed hour from first transaction")
    ax.set_ylabel("Number of transactions")
    ax.legend(title="Class")
    fig.tight_layout()
    fig.savefig(OUTPUT_DIR / "transactions_by_hour.png", dpi=150)
    plt.close(fig)


def format_series(series: pd.Series, precision: int = 6) -> str:
    """Render a Series as a compact Markdown table."""
    rows = ["| Field | Value |", "| --- | ---: |"]
    for label, value in series.items():
        if isinstance(value, float):
            rendered_value = f"{value:.{precision}f}"
        else:
            rendered_value = str(value)
        rows.append(f"| {label} | {rendered_value} |")
    return "\n".join(rows)


def format_dtypes(dtypes: pd.Series) -> str:
    """Render column data types as a Markdown table without extra packages."""
    rows = ["| Column | Data type |", "| --- | --- |"]
    rows.extend(f"| {column} | {dtype} |" for column, dtype in dtypes.items())
    return "\n".join(rows)


def main() -> None:
    if not DATA_PATH.exists():
        raise FileNotFoundError(f"Dataset not found: {DATA_PATH}")

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    sns.set_theme(style="whitegrid")
    data = pd.read_csv(DATA_PATH)

    required_columns = {"Time", "Amount", "Class"}
    missing_required = required_columns.difference(data.columns)
    if missing_required:
        raise ValueError(f"Dataset is missing required columns: {sorted(missing_required)}")

    class_counts = data["Class"].value_counts().sort_index()
    legitimate_count = int(class_counts.get(0, 0))
    fraudulent_count = int(class_counts.get(1, 0))
    fraud_percentage = fraudulent_count / len(data) * 100
    missing_values = data.isna().sum()
    duplicate_rows = int(data.duplicated().sum())
    amount_stats = data["Amount"].describe(percentiles=[0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99])
    time_stats = data["Time"].describe(percentiles=[0.01, 0.05, 0.25, 0.5, 0.75, 0.95, 0.99])
    time_span_hours = (data["Time"].max() - data["Time"].min()) / 3600

    save_class_distribution_plot(class_counts)
    save_amount_distribution_plot(data)
    save_time_by_class_plot(data)

    report = f"""# RiskGuard AI — Phase 1 EDA

Source dataset: `{DATA_PATH.relative_to(PROJECT_ROOT).as_posix()}`  
Raw data was read only; this analysis does not modify it.

## Dataset structure

- Rows: {len(data):,}
- Columns: {len(data.columns):,}
- Column names: {", ".join(data.columns)}

### Data types

{format_dtypes(data.dtypes.astype(str))}

## Missing values

{format_series(missing_values, precision=0)}

## Duplicate rows

- Exact duplicate rows: {duplicate_rows:,}

## Class balance

- Legitimate transactions (`Class == 0`): {legitimate_count:,}
- Fraudulent transactions (`Class == 1`): {fraudulent_count:,}
- Fraud percentage: {fraud_percentage:.12f}%

## Amount statistics

{format_series(amount_stats)}

## Time statistics

`Time` ranges from {data["Time"].min():.0f} to {data["Time"].max():.0f} seconds, spanning {time_span_hours:.2f} hours. It is an elapsed-time field rather than a calendar timestamp, so dates, weekdays, and time zones cannot be inferred.

{format_series(time_stats)}

## Visualizations

- `class_distribution.png` — transaction counts by target class.
- `amount_distribution.png` — amount histogram through the 99th percentile; values above it remain included in all calculated statistics.
- `transactions_by_hour.png` — transaction volumes by elapsed hour and class.

## Observations and data-quality notes

- The target is strongly imbalanced: only {fraud_percentage:.4f}% of transactions are labelled fraudulent.
- The amount distribution is right-skewed: the mean ({data["Amount"].mean():.2f}) exceeds the median ({data["Amount"].median():.2f}), and the maximum is {data["Amount"].max():.2f}.
- Missing values total {int(missing_values.sum()):,} across all columns, and there are {duplicate_rows:,} exact duplicate rows.
- `Time` is measured in seconds from an unspecified starting point, limiting calendar-based interpretation.
- Features `V1` through `V28` are anonymized/transformed; their original business meaning is not available from this dataset alone.
"""
    report_path = OUTPUT_DIR / "eda_report.md"
    report_path.write_text(report, encoding="utf-8")

    print(f"EDA complete. Report: {report_path.relative_to(PROJECT_ROOT)}")
    print(f"Rows: {len(data):,}; columns: {len(data.columns):,}")
    print(f"Legitimate: {legitimate_count:,}; fraudulent: {fraudulent_count:,} ({fraud_percentage:.12f}%)")
    print(f"Exact duplicate rows: {duplicate_rows:,}; total missing values: {int(missing_values.sum()):,}")


if __name__ == "__main__":
    main()
