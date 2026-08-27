"""Optional OpenAI Responses API adapter behind the Phase 10 guardrails.

No request is made when ``AI_PROVIDER_API_KEY`` is absent. All provider
failures return the deterministic fallback through ``guarded_investigation``.
"""

from __future__ import annotations

import json
import logging
import os
from collections.abc import Callable, Mapping
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from ai_guardrails import guarded_investigation


LOGGER = logging.getLogger("riskguard.ai_provider")
DEFAULT_ENDPOINT = "https://api.openai.com/v1/responses"
DEFAULT_MODEL = "gpt-4o-mini"
DEFAULT_TIMEOUT_SECONDS = 20.0
MAX_RESPONSE_BYTES = 64 * 1024
OUTPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["summary", "risk_factors", "evidence", "recommended_action", "confidence"],
    "properties": {
        "summary": {"type": "string"},
        "risk_factors": {"type": "array", "items": {"type": "string"}},
        "evidence": {"type": "array", "items": {"type": "string"}},
        "recommended_action": {
            "type": "string",
            "enum": ["ALLOW", "MONITOR", "STEP_UP_VERIFICATION", "MANUAL_REVIEW", "TEMPORARY_RESTRICTION"],
        },
        "confidence": {"type": "number", "minimum": 0, "maximum": 1},
    },
}


class ProviderError(ValueError):
    """Raised for safe-to-fallback provider failures."""


class OpenAIProvider:
    """Small one-provider adapter; it exposes no tools or arbitrary actions."""

    def __init__(
        self,
        api_key: str | None,
        model: str = DEFAULT_MODEL,
        endpoint: str = DEFAULT_ENDPOINT,
        timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS,
        opener: Callable[..., Any] = urlopen,
    ) -> None:
        self.api_key = api_key.strip() if isinstance(api_key, str) else None
        self.model = model
        self.endpoint = endpoint
        self.timeout_seconds = timeout_seconds
        self.opener = opener

    @classmethod
    def from_env(cls) -> "OpenAIProvider":
        timeout_value = os.environ.get("AI_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))
        try:
            timeout = float(timeout_value)
        except ValueError as error:
            raise ProviderError("AI_TIMEOUT_SECONDS must be numeric") from error
        if not 1.0 <= timeout <= 60.0:
            raise ProviderError("AI_TIMEOUT_SECONDS must be between 1 and 60 seconds")
        return cls(
            os.environ.get("AI_PROVIDER_API_KEY"),
            model=os.environ.get("AI_MODEL", DEFAULT_MODEL),
            timeout_seconds=timeout,
        )

    def _request(self, messages: list[dict[str, str]]) -> str:
        if not self.api_key:
            raise ProviderError("AI_PROVIDER_API_KEY is not configured")
        body = {
            "model": self.model,
            "input": messages,
            "store": False,
            "max_output_tokens": 1_500,
            "text": {
                "format": {
                    "type": "json_schema",
                    "name": "risk_investigation",
                    "strict": True,
                    "schema": OUTPUT_SCHEMA,
                }
            },
        }
        request = Request(
            self.endpoint,
            data=json.dumps(body).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        LOGGER.info("provider_attempted")
        try:
            with self.opener(request, timeout=self.timeout_seconds) as response:
                if getattr(response, "status", 200) != 200:
                    raise ProviderError("provider returned a non-success status")
                payload = response.read(MAX_RESPONSE_BYTES + 1)
        except ProviderError:
            LOGGER.warning("provider_failed")
            raise
        except (HTTPError, URLError, TimeoutError, OSError):
            LOGGER.warning("provider_failed")
            raise ProviderError("provider request failed") from None
        if len(payload) > MAX_RESPONSE_BYTES:
            LOGGER.warning("provider_failed")
            raise ProviderError("provider response exceeded size limit")
        try:
            parsed = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            LOGGER.warning("provider_failed")
            raise ProviderError("provider response was not valid JSON") from error
        output_text = parsed.get("output_text") if isinstance(parsed, Mapping) else None
        if not isinstance(output_text, str):
            output_text = self._extract_output_text(parsed)
        if not output_text:
            LOGGER.warning("provider_failed")
            raise ProviderError("provider response had no structured output")
        LOGGER.info("provider_succeeded")
        return output_text

    @staticmethod
    def _extract_output_text(parsed: Any) -> str | None:
        if not isinstance(parsed, Mapping):
            return None
        for item in parsed.get("output", []):
            if not isinstance(item, Mapping):
                continue
            for content in item.get("content", []):
                if isinstance(content, Mapping) and isinstance(content.get("text"), str):
                    return content["text"]
        return None

    def investigate(self, record: Mapping[str, Any]) -> dict[str, Any]:
        """Use the guarded flow; provider output never becomes risk authority."""
        return guarded_investigation(record, self._request)
