# RiskGuard AI Architecture

## Status

**IMPLEMENTED:** This document describes the current local prototype in this repository. It does not describe an intended production architecture.

## System boundary

```text
REAL DATA: Kaggle transaction fields
                 |
                 v
        Saved XGBoost baseline
                 |
                 v
        ML fraud probability
                 |
SYNTHETIC DEMO DATA: behavioral context
                 |
                 v
       Behavioral signals/points
                 |
                 v
       Deterministic risk engine
             |             |
             v             v
       Risk decision   Rule evidence
             \             /
              v           v
              Deterministic Investigator
                         |
               +---------+---------+
               |                   |
               v                   v
         AI guardrails       Deterministic
       + optional provider      fallback
               \                   /
                v                 v
                    FastAPI API
                         |
               +---------+---------+
               |                   |
               v                   v
          SQLite + audit     Streamlit console
```

The boundary is deliberate: ML predicts; the deterministic risk engine decides; the Investigator explains supplied evidence; optional AI can improve the narrative only. AI cannot override the application-owned ML probability, behavioral points, risk score, risk level, or rule evidence. Human and organizational policy remain responsible for operational action.

## Components and data classification

| Component | Current role | Data classification |
| --- | --- | --- |
| `scripts/train_baselines.py` and saved artifact | Train/reproduce the XGBoost baseline | REAL DATA |
| `scripts/behavioral_context.py` | Generate reproducible context and rule signals | SYNTHETIC DEMO DATA plus real `Amount` |
| `scripts/investigator.py` | Produce deterministic evidence-based investigation output | REAL DATA and SYNTHETIC DEMO DATA already in an assessment |
| `scripts/ai_guardrails.py`, `ai_investigator.py`, `ai_provider.py` | Minimize evidence, validate optional output, and fall back safely | MOCKED DATA in tests; optional external provider only when explicitly configured |
| `api/` | Authenticated investigation and persistence interface | Validated application fields |
| `scripts/database.py` and repository | Store validated investigations and safe audit metadata | No raw vectors, prompts, or credentials |
| `scripts/app.py` | Read-only Streamlit presentation | Stored assessments and safe repository data |

The application does not contain real payment integration or real behavioral history. Mocked provider responses are used by tests and are not live AI evaluation.

## Runtime paths

The API reads saved behavioral assessments, applies the existing Investigator path, and persists validated results to `data/riskguard.db`. `/health` and `/ready` are public; investigation operations require `X-API-Key`. The Streamlit console is a separate local presentation process and is not an authenticated substitute for the API.

See [API](API.md), [MODEL](MODEL.md), [RISK_ENGINE](RISK_ENGINE.md), [AI_AGENT](AI_AGENT.md), [DATABASE](DATABASE.md), and [DASHBOARD](DASHBOARD.md).

## Demo story

1. A reviewer selects a saved transaction assessment, such as source row `215984`.
2. The model probability, transparent behavioral evidence, and deterministic risk score are displayed together.
3. The Investigator explains why the assessment is high risk and states the evidence boundary.
4. Optional AI may provide a validated advisory narrative; otherwise the deterministic fallback is shown.
5. Through the API, the completed investigation and safe audit events can be retrieved from SQLite. No action is executed automatically.

This story is a local demonstration using saved assessments, synthetic context, and mocked provider responses in tests.

## Production-readiness matrix

| Capability | Current evidence | Assessment |
| --- | --- | --- |
| Baseline ML evaluation | Saved metrics and model reports; F1 `0.847458`, PR-AUC `0.821925` | IMPLEMENTED prototype evidence |
| Deterministic risk ownership | Saved risk validation and end-to-end invariants | IMPLEMENTED |
| Explainability/investigation | Deterministic Investigator and saved reports | IMPLEMENTED |
| AI safety boundary | Guardrails, mocked tests, deterministic fallback | IMPLEMENTED; live provider quality is a LIMITATION |
| API validation/authentication | Tests cover auth, bounded input, safe errors, headers, and rate limiting | IMPLEMENTED locally |
| Persistence/auditability | SQLite repository tests and API persistence tests | IMPLEMENTED locally |
| Dashboard | Streamlit AppTest passed; browser test is absent | IMPLEMENTED locally; browser testing LIMITATION |
| Real behavioral history/payment integration | Not present in repository | LIMITATION |
| Live AI evaluation | `live_provider_evaluation` is null in saved metrics | LIMITATION |
| Production scale/high availability | SQLite and limiter are local/process-scoped; no load benchmark | LIMITATION |
| TLS, strong identity, distributed controls, operations | Deployment guidance only | PLANNED / FUTURE |
| Docker runtime validation | No verified runtime test artifact | LIMITATION |

The matrix is a readiness assessment, not a claim of production readiness.

## Phase 1–23 development history

This concise history follows the repository’s commit history and checked-in artifacts:

| Phases | Delivered capability |
| --- | --- |
| 1 | EDA and data-quality reporting |
| 2 | Baseline Logistic Regression/XGBoost modelling and saved metrics |
| 3 | Reproducible synthetic behavioral context and risk scoring |
| 4 | Deterministic Investigator and reports |
| 5A | Streamlit investigation console |
| 6 | Model validation and threshold analysis |
| 7 | Risk-engine validation |
| 8 | Model explainability artifacts |
| 9 | Behavioral signal analysis and richer saved context |
| 10 | AI guardrail/security boundary documentation and tests |
| 11 | Optional AI provider adapter |
| 12 | Guarded application Investigator integration |
| 13 | FastAPI service |
| 14 | End-to-end validation |
| 15 | SQLite persistence |
| 16 | Auditability and repository hardening |
| 17 | Observability and reliability |
| 18 | Database hardening |
| 19 | API authentication |
| 20 | FastAPI hardening |
| 21 | End-to-end security assessment |
| 22 | Investigation console upgrade |
| 23 | Deployment configuration and system evaluation |

The repository contains no Phase 25 work.

## Related evidence

[System evaluation](../reports/evaluation/system_evaluation.md), [system metrics](../reports/evaluation/system_metrics.json), [E2E validation](../reports/e2e/e2e_validation.md), and [security test report](SECURITY_TEST_REPORT.md).
