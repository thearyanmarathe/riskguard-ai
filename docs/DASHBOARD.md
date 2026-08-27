# RiskGuard AI Investigation Console

The Streamlit console is a read-only presentation layer over the existing
investigation repository and saved Phase 3 assessment output. It uses a
read-only aggregate for exact totals plus bounded deterministic repository
reads for displayed rows, and never writes SQLite, calls OpenAI directly,
reloads XGBoost for display, or recalculates risk.

Run locally from the project root:

```powershell
.\.venv\Scripts\python.exe -m streamlit run .\scripts\app.py
```

The console provides persisted overview metrics, LOW/MEDIUM/HIGH distribution,
bounded recent investigations, source-row lookup, detail tabs, stored ML
probability evidence, behavioral rule evidence, the deterministic decision,
advisory AI output, read-only audit history, and safe system status. Empty or
unavailable data produces a friendly state rather than an exception.

`Time`, `Amount`, and `V1`–`V28` are real Kaggle dataset fields; V1–V28 are not
displayed. `user_id`, `device_id`, `region`, `transaction_velocity`,
`historical_average_amount`, and `amount_deviation` are clearly labelled
**SYNTHETIC DEMO BEHAVIORAL METADATA**. They are not customer history and did
not come from the Kaggle dataset.

The deterministic risk engine owns risk score and risk level. AI output is
advisory and fallback status is visible without exposing credentials. Audit
history is limited to safe persisted event metadata. Prompts, keys, raw data,
paths, SQL, and provider responses are not displayed.
