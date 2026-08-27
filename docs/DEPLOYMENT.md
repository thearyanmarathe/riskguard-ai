# RiskGuard AI Deployment Guide

## Architecture

The deployment contains a thin FastAPI service and the existing read-only Streamlit investigation console. The API loads the saved assessment CSV and existing XGBoost artifact, applies the existing Investigator path, and persists investigation records in SQLite. The dashboard reads the existing saved assessments and local SQLite records; it does not replace the API's authentication or decision logic.

The deterministic risk score, behavioral points, risk levels, and Investigator decisions remain authoritative. Optional AI is advisory and falls back deterministically.

## Prerequisites

Python 3.12 is recommended. Install the pinned `requirements.txt`. Docker and Docker Compose are optional for the controlled local container deployment. No PostgreSQL, Redis, external queue, or external service is required.

## Environment Variables

Copy `.env.example` to `.env` for local use. Never commit `.env` or put real credentials in images, Compose files, source, prompts, or logs.

| Variable | Default | Purpose |
|---|---:|---|
| `RISKGUARD_API_KEY` | empty locally | Required non-empty key for protected API routes |
| `AI_PROVIDER_API_KEY` | empty | Optional provider credential; empty selects deterministic fallback |
| `AI_MODEL` | `gpt-4o-mini` | Existing optional provider model setting |
| `AI_TIMEOUT_SECONDS` | `30` | Existing provider timeout |
| `RISKGUARD_LOG_LEVEL` | `INFO` | Allowlisted log level |
| `RISKGUARD_RATE_LIMIT_REQUESTS` | `60` | Process-local request count window |
| `RISKGUARD_RATE_LIMIT_WINDOW_SECONDS` | `60` | Process-local window length |

The current SQLite location is the existing repository default `data/riskguard.db`; there is no new database configuration or schema behavior in this phase.

## Local Development

```powershell
Copy-Item .env.example .env
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

Set a development API key in the untracked `.env`, then run the API and dashboard in separate terminals.

## FastAPI Startup

```powershell
.\.venv\Scripts\python.exe -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

The controlled container command binds to `0.0.0.0` and does not use `--reload`. `/health` is public liveness; protected investigation routes require `X-API-Key`.

## Streamlit Startup

```powershell
.\.venv\Scripts\python.exe -m streamlit run scripts/app.py --server.address 127.0.0.1 --server.port 8501
```

For a container use `streamlit run scripts/app.py --server.address=0.0.0.0 --server.port=8501 --server.headless=true`. The current dashboard is a local read-only console over saved assessments and SQLite; it is not an unauthenticated substitute for the API.

## Docker

Build and run the API image:

```powershell
docker build -t riskguard-ai:local .
docker run --rm -p 8000:8000 -e RISKGUARD_API_KEY=change-me -v riskguard-data:/app/data riskguard-ai:local
```

The image installs only pinned `requirements.txt`, excludes raw CSV, `.git`, `.venv`, `.env`, tests, and runtime databases, runs as UID/GID 10001, and includes only the saved model and assessment artifacts needed by the application.

## Docker Compose

Set `RISKGUARD_API_KEY` in the shell or an untracked `.env`, then:

```powershell
docker compose up --build
```

Compose starts only `api` and `dashboard` and shares the named `riskguard-data` volume for SQLite. It does not add PostgreSQL, Redis, or an external AI service. The API healthcheck gates dashboard startup.

## Health Checks

```powershell
Invoke-WebRequest http://127.0.0.1:8000/health
```

Successful liveness returns HTTP 200 and `{"status":"ok"}`. It does not disclose credentials or internal paths.

## Readiness

```powershell
Invoke-WebRequest http://127.0.0.1:8000/ready
```

Readiness checks SQLite connectivity and loads the existing model artifact. It returns HTTP 503 with a generic body when dependencies are unavailable. It intentionally does not require OpenAI/provider availability because AI is optional and deterministic fallback is supported.

## Authentication

Protected API routes require the configured `RISKGUARD_API_KEY` in `X-API-Key`. Authentication uses constant-time comparison and generic unauthorized responses. Keep the key outside source control and rotate it through the deployment environment. This is a single shared application key, not user identity or role-based access control.

## TLS / Reverse Proxy

Terminate TLS at a managed reverse proxy or ingress in front of the API and dashboard. Use a trusted certificate, redirect HTTP to HTTPS, restrict exposed ports, set proxy timeouts/body limits consistent with the API, and forward only the headers required by the deployment. Do not put private keys in this repository or image. The application does not generate certificates.

## Database

SQLite remains the existing local persistence layer. The application initializes the existing schema safely, enables foreign keys and WAL mode, and uses a busy timeout. Mount only the application data directory (or use the Compose named volume). Do not mount the raw Kaggle CSV as a runtime volume. SQLite is appropriate for a controlled local/single-process demonstration, not a multi-replica write-heavy service.

## Backup Strategy

Back up `data/riskguard.db` using a SQLite-aware or application-quiesced copy procedure. Include retention, encryption at rest, access control, restore testing, and a documented recovery point/objective. Do not back up secrets into the same archive. For a production workload, migrate to an operationally managed database after a separate design and migration phase.

## Logging

Logs are structured and allowlisted. They record event type, endpoint, status, duration, request ID, and safe error category only; they do not log API keys, provider keys, raw transaction fields, prompts, model features, or full tracebacks to clients. Route logs to a protected sink with retention and access controls. Review log volume and disk limits at the proxy/container runtime.

## Rate Limiting

The existing limiter is process-local and applies to protected operations. Defaults are 60 requests per 60 seconds with bounded tracked clients. It is not a distributed limiter; multiple replicas require a separate shared gateway/limiter design. Do not disable it for convenience.

## Secrets

Use environment injection or a secret manager. Do not bake credentials into Docker layers, Compose YAML, reports, logs, browser bundles, or command history. Keep `.env` untracked. An empty AI key is the safe default and selects deterministic fallback; an empty API key intentionally prevents protected access.

## Resource Limits

Set CPU, memory, process, request-body, proxy, timeout, and log-retention limits at the container/orchestrator and reverse-proxy layers. The API already enforces a bounded request body and bounded list query. Do not run with debug mode or auto-reload in production.

## Production Considerations

Use HTTPS, secret rotation, least-privilege runtime identity, image scanning/signing, pinned dependency review, protected artifact storage, database backups, centralized monitoring, alerting, and incident response. Run one controlled API process per container and use an external reverse proxy for ingress. The dashboard should be access-controlled at the proxy/identity layer if exposed beyond a local workstation.

## Known Limitations

This is a demonstration deployment, not a production-validated fraud system. The model is a baseline, behavioral metadata is synthetic, the score is not a calibrated fraud probability, SQLite and the rate limiter are local/process-scoped, and authentication is a single API key. The saved model and assessment artifacts must be provenance-controlled. Provider quality, throughput, concurrency, disaster recovery, and multi-replica behavior require separate validation. Docker smoke testing depends on a functioning local Docker daemon.
