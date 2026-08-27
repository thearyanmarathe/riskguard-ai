# AI Provider Configuration — Phase 11

RiskGuard AI uses one optional provider adapter: the OpenAI Responses API. The adapter is not required for the application or tests. If no key is configured, `ApplicationInvestigator` returns the existing deterministic Investigator report.

## Configuration

Set environment variables outside source control:

```powershell
$env:AI_PROVIDER_API_KEY = "<provider-key>"
$env:AI_MODEL = "gpt-4o-mini"
$env:AI_TIMEOUT_SECONDS = "20"
```

`.env.example` contains placeholders only. Do not create or commit a real `.env` file, and do not put a key in code, prompts, reports, tests, or logs.

## Flow

`run_investigator.py` and the dashboard use `ApplicationInvestigator`. It always creates the deterministic report first. When configured, `OpenAIProvider.investigate(record)` uses the existing guarded flow: only minimized messages from `build_ai_messages` are sent, strict JSON-schema output is requested, and `validate_ai_output` is applied. Validated AI fields are advisory and are merged with the deterministic report; saved numeric risk values and rule evidence remain authoritative.

The deterministic risk score, ML probability, behavioral points, and risk level are never taken from provider output. The AI can only return an explanation and one value from the fixed action policy. No application action is executed; recommendations are advisory only.

## Failure behavior

Missing key, timeout, HTTP failure, oversized/malformed provider response, invalid JSON, invalid action, invalid confidence, prompt-exfiltration content, or score-tampering fields all produce the deterministic fallback. There is no retry loop. The request timeout is finite and the response body is bounded. The CLI and dashboard expose whether the result came from the optional provider or deterministic fallback without changing existing risk presentation.

## Testing without a key

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q scripts tests
```

Tests use mocked provider responses and make no paid external API calls.
