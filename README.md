# RiskGuard AI

RiskGuard AI is a student project demonstrating a reproducible credit-card fraud investigation workflow. It combines a baseline XGBoost fraud probability from the Kaggle credit-card dataset with transparent behavioral rules and a deterministic, evidence-only investigation summary.

It is a demonstration project, not a production fraud system or a production-validated financial risk score.

## Problem statement

Credit-card fraud datasets are highly imbalanced: the positive class is rare, so accuracy alone can be misleading. This project demonstrates data quality checks, imbalance-aware baseline modelling, explicit rule signals, and an auditable investigation experience.

## Architecture

```text
Raw Kaggle CSV (read only)
        |
        +-- EDA report and figures
        |
        +-- Deduplicated in-memory train/test split --> XGBoost baseline --> saved model artifact
                                                        |
Real Kaggle transaction subset ------------------------+--> ML fraud probability
        |
Synthetic demo context --> behavioral rules -----------> transparent risk score
                                                        |
                                             deterministic investigator
                                                        |
                                              Streamlit dashboard
```

The Streamlit application is a UI layer. It reads saved Phase 3 assessments and reuses the deterministic investigator; it does not retrain models, regenerate metadata, or recalculate the risk formula.

## Dataset and provenance

Place the Kaggle `creditcard.csv` file at `data/raw/creditcard.csv`.

Real Kaggle fields are `Time`, `V1`–`V28`, `Amount`, and `Class`. The `V` fields are anonymized/transformed dataset features. The raw CSV is read only and is excluded from Git.

`user_id`, `device_id`, `region`, and `transaction_velocity` are **synthetic demo metadata** created deterministically for the Phase 3 illustration. They do not come from Kaggle, are not inputs to XGBoost, and are not claimed to improve the ML model.

## ML approach

Phase 2 removes exact duplicate records only from an in-memory derived dataframe before the split, preventing identical records from crossing train/test boundaries. The train/test split is stratified by `Class` with a fixed seed. Logistic Regression uses `class_weight="balanced"`; the XGBoost baseline uses the same fixed, simple configuration throughout the project. Extensive hyperparameter tuning was intentionally not performed.

On the held-out test set, the XGBoost baseline achieved:

| Metric | Result |
| --- | ---: |
| Precision | 0.914634 |
| Recall | 0.789474 |
| F1-score | 0.847458 |
| PR-AUC / Average Precision | 0.821925 |

Accuracy is not the primary metric because a classifier predicting every transaction as legitimate would appear highly accurate while detecting no fraud.

The evaluated XGBoost artifact is saved as `reports/model/xgboost_baseline.json`. Its per-transaction probabilities are calculated from real Kaggle transaction features only: `Time`, `V1`–`V28`, and `Amount`.

## Behavioral rule engine

Phase 3 selects a reproducible 5,000-row subset and applies transparent rules to synthetic demo context plus the real `Amount` field:

| Rule | Points |
| --- | ---: |
| High transaction velocity | 20 |
| Unusual synthetic device | 20 |
| Unusual synthetic region | 15 |
| High amount | 20 |

The deterministic formula is:

```text
min(100, 60 × ml_fraud_probability + behavioral rule points)
```

It produces LOW, MEDIUM, and HIGH levels. This formula is intentionally transparent for demonstration and is not a production-validated financial risk score.

## AI Investigator

The Phase 4 investigator receives one saved assessment record and produces a structured, human-readable summary, rule evidence, conservative recommendation, and evidence boundary. It is deterministic, requires no API key or external service, and uses only supplied assessment fields and stored rule explanations. It does not infer customer history, motives, account compromise, real locations, or proof of fraud.

## Dashboard

The Phase 5A Streamlit dashboard displays a selected saved transaction's risk summary, real transaction details, clearly labelled synthetic demo context, triggered rules, signal contributions, and the reused deterministic investigator output.

## Project structure

```text
data/raw/                         # local Kaggle CSV; ignored by Git
scripts/eda.py                    # Phase 1 EDA
scripts/train_baselines.py        # Phase 2 baseline training and artifact save
scripts/behavioral_context.py     # Phase 3 reusable synthetic/risk logic
scripts/run_behavioral_demo.py    # Phase 3 output generation
scripts/investigator.py           # Phase 4 deterministic investigator
scripts/run_investigator.py       # Phase 4 report generation
scripts/app.py                    # Phase 5A Streamlit UI
reports/eda/                      # EDA outputs
reports/model/                    # baseline metrics, plots, model artifact
reports/behavioral/               # saved behavioral assessments
reports/investigator/             # sample investigation reports
```

## Setup

Create or activate the project virtual environment, install the existing dependencies, and ensure `data/raw/creditcard.csv` is present. Streamlit is required for the dashboard.

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## Run commands

Run each command from the project root (`riskguard-ai`).

```powershell
# Phase 1: EDA
.\.venv\Scripts\python.exe .\scripts\eda.py

# Phase 2: reproduce baseline training and save the XGBoost artifact
.\.venv\Scripts\python.exe .\scripts\train_baselines.py

# Phase 3: generate deterministic behavioral assessments
.\.venv\Scripts\python.exe .\scripts\run_behavioral_demo.py

# Phase 4: generate representative investigation reports
.\.venv\Scripts\python.exe .\scripts\run_investigator.py

# Phase 5A: start the dashboard
.\.venv\Scripts\python.exe -m streamlit run .\scripts\app.py
```

To investigate one existing Phase 3 source row:

```powershell
.\.venv\Scripts\python.exe .\scripts\run_investigator.py --source-row-id 215984
```

## Limitations and disclaimer

- The data contains anonymized features, limiting business interpretation.
- Fraud is extremely rare, so results should be interpreted with class imbalance in mind.
- Synthetic behavioral fields are demo-only and do not represent real users, devices, regions, or velocity history.
- The risk score and recommendations are transparent project demonstrations, not financial advice or a production fraud decision.
- A high probability or risk level is an investigation signal; it does not prove fraud.
