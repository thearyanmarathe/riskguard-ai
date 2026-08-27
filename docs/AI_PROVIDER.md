# AI Provider Configuration — Phase 11

RiskGuard AI uses one optional provider adapter: the OpenAI Responses API. The adapter is not required for the application or tests. If no key is configured, `OpenAIProvider.investigate()` returns the deterministic fallback.

## Configuration

Set environment variables outside source control:

```powershell
$env:AI_PROVIDER_API_KEY = "<provider-key>"
$env:AI_MODEL = "gpt-4o-mini"
$env:AI_TIMEOUT_SECONDS = "20"
```

`.env.example` contains placeholders only. Do not create or commit a real `.env` file, and do not put a key in code, prompts, reports, tests, or logs.

## Flow

`OpenAIProvider.investigate(record)` calls the existing guarded flow. The adapter sends only messages from `build_ai_messages`, requests strict JSON-schema output, parses the response, and relies on `guarded_investigation` to call `validate_ai_output`. It sends no raw CSV, full dataset, tools, shell commands, file operations, or unrestricted network requests.

The deterministic risk score, ML probability, behavioral points, and risk level are not part of the AI control surface. The AI can only return an explanation and one value from the fixed action policy.

## Failure behavior

Missing key, timeout, HTTP failure, oversized/malformed provider response, invalid JSON, invalid action, invalid confidence, prompt-exfiltration content, or score-tampering fields all produce the deterministic fallback. There is no retry loop. The request timeout is finite and the response body is bounded.

## Testing without a key

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q scripts tests
```

Tests use mocked provider responses and make no paid external API calls.
