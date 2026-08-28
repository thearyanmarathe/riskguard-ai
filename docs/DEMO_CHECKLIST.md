# RiskGuard AI Demo Checklist

## Environment

- [ ] Activate the project virtual environment.
- [ ] Dependencies are installed.
- [ ] Working directory is `riskguard-ai`.
- [ ] `data/riskguard.db` is available.
- [ ] Saved model artifact is available.
- [ ] No OpenAI key is required for the primary demo.
- [ ] No real secrets are displayed or placed in shell history.

## System

- [ ] API health is available through the existing service/test path.
- [ ] API readiness is available through the existing service/test path.
- [ ] Dashboard starts locally.
- [ ] Demo runner passes.
- [ ] SQLite integrity is `ok`.
- [ ] Model SHA-256 matches the documented artifact hash.

## Demo flow

- [ ] LOW scenario: source row `28727`, score `20.95`.
- [ ] MEDIUM scenario: source row `233005`, score `40.13`.
- [ ] HIGH scenario: source row `215984`, score `95.00`.
- [ ] HIGH rules are visible: unusual region and high amount deviation.
- [ ] Deterministic fallback status is visible.
- [ ] Advisory recommendation is visible.
- [ ] Audit history is visible for a persisted investigation.
- [ ] REAL DATA and SYNTHETIC DEMO DATA labels are visible.

## Security

- [ ] No API key is displayed.
- [ ] No secrets or provider credentials are displayed.
- [ ] No raw CSV contents are exposed.
- [ ] No prompts are exposed.
- [ ] V1–V28 vectors are not displayed unnecessarily.
- [ ] No live OpenAI call is made.

## Commands

```powershell
.\.venv\Scripts\Activate.ps1
.\.venv\Scripts\python.exe scripts\run_demo.py
.\.venv\Scripts\python.exe scripts\run_demo.py --scenario high_risk
.\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8765
.\.venv\Scripts\python.exe -m streamlit run scripts\app.py
```

The API and dashboard commands are documented launch commands. Their verification status is recorded in [demo_readiness.md](../reports/demo/demo_readiness.md).

## Git

- [ ] Review `git status` before the final demo.
- [ ] Do not run `git add`, `git commit`, or `git push` as part of demo preparation.
