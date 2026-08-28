# RiskGuard AI

RiskGuard AI is a reproducible fraud-risk investigation prototype. It demonstrates how a fraud prediction can be combined with transparent behavioral evidence and a deterministic investigation workflow.

## What It Does

Fraud detection alone does not provide enough context for investigation. RiskGuard AI combines:

- ML fraud prediction from the Kaggle credit-card dataset
- deterministic behavioral risk signals using synthetic demo metadata
- transparent risk scoring and risk levels
- evidence-based investigation and explainability
- an optional, guarded AI-assisted investigation path
- a FastAPI interface
- SQLite persistence and append-only audit events
- authentication, validation, rate limiting, safe errors, logging, request IDs, and readiness checks

The responsibilities are intentionally separate:

- **ML predicts** a fraud probability.
- **The risk engine decides** the deterministic score and risk level.
- **The Investigator explains** the stored evidence and provides a conservative recommendation.
- **AI is advisory** and may be unavailable; deterministic fallback remains available.
- **Human and organizational policy remain responsible** for operational action.

This is an implemented local demonstration, not a production fraud system or a production-validated financial risk score.

## Architecture

```text
Real Kaggle transaction
          |
          v
  XGBoost baseline model ------> ML fraud probability
          |                                  |
          +---- synthetic demo context ------+
                         |
                         v
              Behavioral signals and points
                         |
                         v
              Deterministic risk engine
                  |                 |
                  v                 v
             Risk decision     Rule evidence
                  \                 /
                   v               v
                    Deterministic Investigator
                              |
                    +---------+---------+
                    |                   |
                    v                   v
              AI guardrails       Deterministic
              + optional AI          fallback
                    \                   /
                     v                 v
                         FastAPI
                           |
                 +---------+---------+
                 |                   |
                 v                   v
        SQLite investigations   Streamlit console
        + audit events          (read-only presentation)
```

The API and dashboard reuse saved assessments and the existing application modules. The dashboard does not retrain the model, call the provider directly, write SQLite, or recalculate the risk formula.

## Data and model

Place the Kaggle file at `data/raw/creditcard.csv`. The real fields are `Time`, `V1`-`V28`, `Amount`, and `Class`; the `V` fields are anonymized/transformed features. The raw CSV is read-only for this application and is excluded from Git.

`user_id`, `device_id`, `region`, `transaction_velocity`, `historical_average_amount`, and `amount_deviation` are deterministic **synthetic demo behavioral metadata**. They are not Kaggle fields, real behavioral history, or inputs to XGBoost.

The saved XGBoost baseline uses a fixed, stratified 80/20 split after in-memory exact-duplicate removal. Verified held-out metrics are:

| Metric | Result |
| --- | ---: |
| Precision | 0.914634 |
| Recall | 0.789474 |
| F1 | 0.847458 |
| Average Precision / PR-AUC | 0.821925 |

The model artifact and supporting evidence are in `reports/model/`. These metrics are a baseline evaluation, not a production performance guarantee.

## Risk and investigation behavior

The implemented deterministic score is:

```text
min(100, 60 * ml_fraud_probability + behavioral rule points)
```

The current risk levels are LOW, MEDIUM, and HIGH. The score is intentionally transparent and is not a calibrated fraud probability.

The deterministic Investigator uses only supplied assessment fields and stored rule explanations. It does not infer customer history, motives, account compromise, real locations, or proof of fraud. If the optional provider is not configured or fails validation, the application uses the deterministic fallback. No recommendation is executed automatically.

## Interfaces and persistence

- **FastAPI:** `POST /investigate`, `GET /investigations`, and `GET /investigations/{id}` are protected by `X-API-Key`; `/health` and `/ready` are public.
- **SQLite:** completed investigations and safe audit metadata are stored in `data/riskguard.db`. Raw CSV rows, feature vectors, prompts, and credentials are not stored.
- **Streamlit:** the local investigation console presents saved assessments, risk evidence, investigation output, and audit metadata without changing the underlying decision.

## Demo

Run the three deterministic LOW, MEDIUM, and HIGH scenarios:

```powershell
.\.venv\Scripts\python.exe scripts\run_demo.py
```

The demo uses selected real dataset rows with synthetic behavioral context and deterministic fallback. See [docs/DEMO.md](docs/DEMO.md).

See the detailed documentation:

- [Architecture, demo story, readiness matrix, and Phase 1-23 history](docs/ARCHITECTURE.md)
- [Model](docs/MODEL.md)
- [Risk engine](docs/RISK_ENGINE.md)
- [AI Investigator/agent boundary](docs/AI_AGENT.md)
- [API](docs/API.md)
- [Security](docs/SECURITY.md) and [threat model](docs/THREAT_MODEL.md)
- [Database](docs/DATABASE.md)
- [Observability](docs/OBSERVABILITY.md)
- [Dashboard](docs/DASHBOARD.md)
- [Optional AI provider](docs/AI_PROVIDER.md)
- [Deployment](docs/DEPLOYMENT.md)
- [Security test report](docs/SECURITY_TEST_REPORT.md)

## Repository map

```text
api/                    FastAPI routes, schemas, authentication, rate limiting
scripts/                EDA, model, behavioral, investigator, API support, and UI code
tests/                  Unit, integration, security, persistence, and Streamlit AppTest coverage
reports/model/          Saved baseline metrics, plots, and explainability artifacts
reports/behavioral/     Saved synthetic-context assessments and analyses
reports/risk/           Risk-engine validation artifacts
reports/investigator/   Representative investigation outputs
reports/evaluation/     System evaluation and machine-readable metrics
data/raw/               Local Kaggle CSV; ignored by Git
```

## Setup

Run commands from `riskguard-ai` with the existing virtual environment and dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Ensure `data/raw/creditcard.csv` is present before running data or assessment generation commands.

## Run locally

```powershell
# Generate or refresh the existing analytical artifacts, when needed
.\.venv\Scripts\python.exe .\scripts\eda.py
.\.venv\Scripts\python.exe .\scripts\train_baselines.py
.\.venv\Scripts\python.exe .\scripts\run_behavioral_demo.py
.\.venv\Scripts\python.exe .\scripts\run_investigator.py

# Start the Streamlit investigation console
.\.venv\Scripts\python.exe -m streamlit run .\scripts\app.py

# Start the API in another terminal
$env:RISKGUARD_API_KEY = "local-development-key"
.\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

Initialize the local SQLite database, if necessary:

```powershell
.\.venv\Scripts\python.exe .\scripts\init_db.py
```

The optional provider uses `AI_PROVIDER_API_KEY`, `AI_MODEL`, and `AI_TIMEOUT_SECONDS`. Without a provider key, deterministic fallback is the expected path. Never commit `.env` or real credentials.

## Verification

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q scripts tests
```

The checked-in system-evaluation artifact records 86 passed tests and 9 passed end-to-end checks. The current Phase 24 verification run passed 99 tests and 9 end-to-end checks. No live AI-provider evaluation was performed; Streamlit AppTest was used, and browser-level testing was not performed.

## Limitations and future work

**IMPLEMENTED:** reproducible baseline modelling, transparent synthetic behavioral rules, deterministic risk ownership, guarded optional AI with fallback, local API access, SQLite persistence/auditability, and documented security controls.

**LIMITATION:** the dataset is historical and imbalanced; features are anonymized; behavioral context is synthetic; there is no real payment integration or production behavioral history; SQLite and rate limiting are local/process-scoped; authentication is a single shared API key; and the score is not calibrated.

**PLANNED / FUTURE:** live provider-quality evaluation, calibration and drift studies, production load/concurrency testing, stronger identity and authorization, distributed rate limiting, TLS/gateway validation, and production database/retention operations.

Do not interpret a high probability, risk score, or risk level as proof of fraud or as an automatic financial decision.
