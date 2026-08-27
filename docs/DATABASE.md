# RiskGuard AI SQLite Persistence

Phase 15 adds a local SQLite store for completed, validated investigation
results. The database is storage only: prediction, risk scoring, behavioral
rules, and AI guardrails remain in the existing application modules.

## Location and initialization

The default database is `data/riskguard.db`. It is outside `data/raw/` and is
ignored by Git. Initialize it safely with:

```powershell
.\.venv\Scripts\python.exe scripts\init_db.py
```

Initialization creates missing tables and does not delete existing records.

## Schema

The `investigations` table stores `id`, `source_row_id`, `amount`,
`ml_fraud_probability`, `behavioral_points`, `risk_score`, `risk_level`,
validated JSON text for `triggered_rules`, `risk_factors`, and `evidence`,
`investigation_summary`, `recommended_action`, optional `confidence`,
`provider_used`, `fallback_used`, and UTC `created_at`.

No raw CSV rows, V1–V28 vectors, prompts, API keys, provider credentials, or
filesystem paths are stored. JSON/list fields are validated before insertion.

## Repository and API behavior

`scripts/database.py` owns the SQLAlchemy SQLite engine and sessions.
`scripts/investigation_repository.py` owns table access and validation. The
repository performs no risk calculations and uses ORM/parameterized queries.

`POST /investigate` runs the existing Application Investigator first, then
persists its validated result and returns `persistence_id` and `created_at`.
Repeated POST requests create new records; no distributed idempotency rule is
introduced. Use `GET /investigations/{id}` to retrieve one record or
`GET /investigations?source_row_id=<id>&limit=<n>` for a bounded recent list.

The Streamlit dashboard is intentionally unchanged. Persistence is currently
exposed through the API layer only.

## Retention and testing

This demonstration database has no automated retention policy. Local users
should remove old records according to their environment's requirements. Do
not place production secrets or raw transaction data in this database.

Tests use temporary SQLite files and verify initialization, reopening,
repository operations, API persistence, fallback behavior, and raw CSV hash
stability. No existing developer database is required.
