# RiskGuard AI Demo Readiness

## Verification date

2026-08-28. No live OpenAI request was made.

## Demo runner result

`scripts/run_demo.py` passed for the complete three-scenario run and for all
single-scenario modes: `low_risk`, `medium_risk`, and `high_risk`. Each run
ended with `Demo validation: PASSED`.

The runner uses saved assessment records and the existing Investigator path.
It does not retrain, recalculate the risk formula, persist investigations, or
call an external provider.

## Scenario results

| Scenario | Source row | ML probability | Behavioral points | Risk score | Risk level | Rules |
| --- | ---: | ---: | ---: | ---: | --- | --- |
| LOW | 28727 | 0.01587517 | 20 | 20.95 | LOW | unusual_device |
| MEDIUM | 233005 | 0.002242215 | 40 | 40.13 | MEDIUM | high_transaction_velocity; unusual_device |
| HIGH | 215984 | 0.9999875 | 35 | 95.00 | HIGH | unusual_region; high_amount_deviation |

## AI fallback

The demo deliberately uses the deterministic fallback. The provider is
optional, no key is required, and no live AI quality claim is made. Provider
responses used by tests elsewhere are **MOCKED DATA**.

## Database state

The demo runner and final regression tests left the live database unchanged:

- Investigations: 287 before and after
- Audit events: 402 before and after
- SQLite integrity: `ok`
- Database hash during final isolated regression: unchanged

E2E was run in a temporary verification copy because the E2E script writes
its own report JSON. No live database reset or cleanup was performed by the
demo runner.

## Integrity

| Artifact | SHA-256 |
| --- | --- |
| `data/raw/creditcard.csv` | `76274B691B16A6C49D3F159C883398E03CCD6D1EE12D9D8EE38F4B4B98551A89` |
| `reports/model/xgboost_baseline.json` | `D215AC326A5D6C10A29AA6DB0A62D921F8D0DAF5FE8CA0BF5C197F524EFB7B77` |

Both matched before and after verification.

## Tests and checks

- Full unittest discovery: 108 passed, 0 failed
- Compilation: passed
- `pip check`: passed
- E2E: 9 passed, 0 failed
- Streamlit AppTest: passed, 0 exceptions
- Security review: no secrets were displayed; no raw CSV, prompts, or V1–V28 vectors were exposed by the demo flow

## Limitations

This is a local prototype relevant to payment-risk investigation, not a
Razorpay integration. It does not use Razorpay data, claim Razorpay
partnership or endorsement, simulate real payment processing, use real
behavioral history, evaluate a live AI provider, perform browser-level tests,
or validate Docker runtime behavior. AI recommendations are advisory and no
automatic financial action is executed.
