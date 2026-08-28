# RiskGuard AI Submission Summary

### Project Title

RiskGuard AI

### Problem

A single fraud probability does not give an investigator enough context. Fraud-risk review needs interpretable evidence, deterministic decision ownership, and safe handling of optional AI assistance.

### Solution

RiskGuard combines a saved XGBoost fraud probability, synthetic but reproducible behavioral signals, a deterministic risk engine, an evidence-based Investigator, and an optional guarded AI explanation layer.

### Key Features

- ML prediction using real Kaggle transaction fields
- Transparent behavioral evidence
- Application-owned LOW/MEDIUM/HIGH risk decision
- Deterministic fallback when AI is unavailable
- FastAPI access with authentication and validation
- SQLite investigation persistence and audit events
- Read-only Streamlit Investigation Console
- Security controls and reproducible demo scenarios

### Architecture

`REAL transaction data -> ML probability -> SYNTHETIC behavioral evidence -> deterministic risk engine -> Investigator -> optional guarded AI/fallback -> FastAPI/SQLite/Streamlit`

ML predicts. The deterministic risk engine decides. AI explains. Human policy remains responsible for action. See [architecture](ARCHITECTURE.md).

### ML Results

Held-out baseline: 56,746 rows; precision `0.914634`, recall `0.789474`, F1 `0.847458`, PR-AUC `0.821925`. These are baseline dataset measurements, not production guarantees. See [model](MODEL.md).

### Security

API-key authentication, strict bounded validation, request limits, process-local rate limiting, safe errors, security headers, structured observability, prompt-injection defenses, secret redaction, and append-only audit events are implemented. See [security](SECURITY.md).

### AI Safety

AI receives minimized guarded evidence and passes strict output validation. It cannot override probability, behavioral points, score, risk level, or deterministic rules. Provider failure uses deterministic fallback. Provider tests use MOCKED DATA; no live AI evaluation is claimed. See [AI agent boundary](AI_AGENT.md).

### Demo

Run:

```powershell
.\.venv\Scripts\python.exe scripts\run_demo.py
```

The demo uses saved LOW, MEDIUM, and HIGH scenarios and centers on HIGH source row `215984`. See [DEMO_SCRIPT.md](DEMO_SCRIPT.md).

### Limitations

Synthetic behavioral context is not real history; the dataset is anonymized; there is no Razorpay or real payment integration; SQLite and rate limiting are local; optional AI is not live-tested; and no production identity, TLS, monitoring, or scale validation exists.

### Future Work

Production database/retention, stronger identity, distributed controls, model monitoring, controlled AI evaluation, real behavioral history, and payment-platform integration.

### Repository Structure

See the [repository map in the README](../README.md#repository-map) and the [documentation index](../README.md#see-the-detailed-documentation).

### How To Run

Install existing dependencies, ensure the local Kaggle CSV and saved assessment artifacts are available, then use the commands in [DEMO_CHECKLIST.md](DEMO_CHECKLIST.md) and [DEPLOYMENT.md](DEPLOYMENT.md).
