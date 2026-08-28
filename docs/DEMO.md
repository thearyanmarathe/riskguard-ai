# RiskGuard AI Demo

## Demo Goal

The demo shows how one saved transaction assessment moves through the existing investigation path. It uses three real Kaggle source rows, their saved ML outputs, and the existing synthetic behavioral context.

The boundary remains: **ML predicts. The deterministic risk engine decides. AI investigates/explains. AI cannot override authoritative risk values.**

## Scenario Overview

| Scenario | Source row | Expected result | Triggered rules |
| --- | ---: | --- | --- |
| LOW — Normal transaction / low risk | 28727 | 20.95 / LOW | Unusual Device |
| MEDIUM — Behavioral anomaly / medium risk | 233005 | 40.13 / MEDIUM | High Transaction Velocity; Unusual Device |
| HIGH — Multiple suspicious signals / high risk | 215984 | 95.00 / HIGH | Unusual Region; High Amount Deviation |

These are selected from existing saved assessments; the demo does not alter source transactions.

## LOW Scenario

Source row `28727` has ML probability `0.01587517`, 20 behavioral points, and saved risk score `20.95` (LOW). The saved evidence contains one synthetic device anomaly.

## MEDIUM Scenario

Source row `233005` has ML probability `0.002242215`, 40 behavioral points, and saved risk score `40.13` (MEDIUM). The saved evidence contains synthetic high velocity and device signals.

## HIGH Scenario

Source row `215984` has ML probability `0.9999875`, 35 behavioral points, and saved risk score `95.00` (HIGH). The saved evidence contains synthetic region and amount-deviation signals.

## How To Run

From the repository root:

```powershell
.\.venv\Scripts\python.exe scripts\run_demo.py
```

Optional single-scenario mode:

```powershell
.\.venv\Scripts\python.exe scripts\run_demo.py --scenario low_risk
```

The runner reads `demo/scenarios.json` and `reports/behavioral/behavioral_risk_assessments.csv`, invokes the existing `ApplicationInvestigator`, validates the returned values, and performs no persistence. It requires no OpenAI key, network, cloud service, Docker, PostgreSQL, or Redis.

## Expected Results

The CLI prints LOW, MEDIUM, and HIGH in manifest order and ends with `Demo validation: PASSED`. Running it repeatedly should preserve scenario IDs, source rows, risk levels, scores, ML probabilities, behavioral points, triggered rules, and deterministic fallback state.

## Data Provenance

### Real Data

The source-row IDs refer to real Kaggle transaction rows. The assessment file contains the saved ML outputs and authoritative saved risk values. The original Kaggle CSV is not copied or modified.

### Synthetic Data

Behavioral history, historical average amount, amount deviation, device context, region context, and transaction velocity are synthetic demonstration metadata. They are not real customer history.

### AI

Optional. This demo deliberately uses the deterministic fallback and makes no provider call. MOCKED provider responses exist only in tests and are not live AI evaluation.

## Risk Ownership

The runner consumes application-owned risk values and does not recalculate the risk formula or create an alternate prediction path. The Investigator explains stored evidence. No recommendation is executed automatically.

## What The Demo Does Not Represent

**LIMITATION:** This is not a production payment simulation, production performance test, real behavioral-history demonstration, live AI evaluation, browser test, or Docker runtime test. A high probability, score, or level is an investigation signal and does not prove fraud.

Related documentation: [architecture](ARCHITECTURE.md), [model](MODEL.md), [risk engine](RISK_ENGINE.md), [AI agent boundary](AI_AGENT.md), and [system evaluation](../reports/evaluation/system_evaluation.md).
