# RiskGuard AI Investigation Console

**IMPLEMENTED:** The Streamlit console is a read-only presentation layer over the existing
investigation repository and saved Phase 3 assessment output. It uses a
read-only aggregate for exact totals plus bounded deterministic repository
reads for displayed rows, and never writes SQLite, calls OpenAI directly,
reloads XGBoost for display, or recalculates risk.

Run locally from the project root:

```powershell
.\.venv\Scripts\python.exe -m streamlit run .\scripts\app.py
```

The console is a two-workspace Streamlit layout with a dark risk-ops theme.
The sidebar switches between **Overview** and **Investigation** and shows compact
system status. Overview shows persisted KPI metrics, a colored LOW/MEDIUM/HIGH
distribution, and a selectable recent-investigations table. Selecting a row
opens Investigation, which keeps source-row lookup, a risk badge, a display-only
0–100 score bar, and the existing detail tabs (overview context, stored ML
probability evidence, behavioral rule evidence, the deterministic decision,
advisory AI output, and read-only audit history). Empty or unavailable data
produces a friendly state rather than an exception.

`Time`, `Amount`, and `V1`–`V28` are real Kaggle dataset fields; V1–V28 are not
displayed. `user_id`, `device_id`, `region`, `transaction_velocity`,
`historical_average_amount`, and `amount_deviation` are clearly labelled
**SYNTHETIC DEMO BEHAVIORAL METADATA**. They are not customer history and did
not come from the Kaggle dataset.

The deterministic risk engine owns risk score and risk level. AI output is
advisory and fallback status is visible without exposing credentials. Audit
history is limited to safe persisted event metadata. Prompts, keys, raw data,
paths, SQL, and provider responses are not displayed.

**LIMITATION:** Streamlit AppTest is covered by the saved evaluation; browser-level testing is not claimed. The console is local and is not a production access-control boundary.

Related documentation: [architecture](ARCHITECTURE.md), [AI agent boundary](AI_AGENT.md),
[database](DATABASE.md), and [deployment](DEPLOYMENT.md).
