"""Controlled application integration for the optional AI Investigator.

The deterministic Investigator owns all numeric risk values.  The optional
provider can only supply a validated, advisory explanation and always falls
back to the deterministic report.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Mapping
from typing import Any

from ai_provider import OpenAIProvider
from ai_guardrails import validate_ai_output
from investigator import DeterministicInvestigator
from observability import duration_ms, log_event


LOGGER = logging.getLogger("riskguard.ai_investigator")


class ApplicationInvestigator:
    """Run the existing Investigator with an optional guarded AI explanation."""

    def __init__(
        self,
        provider: Any | None = None,
        provider_factory: Callable[[], Any] = OpenAIProvider.from_env,
    ) -> None:
        self.deterministic = DeterministicInvestigator()
        self.provider = provider
        self.provider_factory = provider_factory

    @staticmethod
    def _fallback(report: dict[str, Any], status: str) -> dict[str, Any]:
        result = dict(report)
        result.update(
            {
                "provider_used": False,
                "fallback_used": True,
                "investigation_mode": "Deterministic Investigator",
                "provider_status": status,
            }
        )
        return result

    def investigate(self, record: Mapping[str, Any]) -> dict[str, Any]:
        deterministic = self.deterministic.investigate(record)
        provider = self.provider
        if provider is None:
            try:
                provider = self.provider_factory()
            except Exception:
                LOGGER.info("provider_configuration_unavailable")
                log_event("AI_FALLBACK", provider_mode="optional", fallback_used=True)
                return self._fallback(deterministic, "not_configured")

        if not getattr(provider, "api_key", None):
            log_event("AI_FALLBACK", provider_mode="optional", fallback_used=True)
            return self._fallback(deterministic, "not_configured")

        started = time.perf_counter()
        log_event("AI_STARTED", provider_mode="optional")
        try:
            ai_result = provider.investigate(record)
            if not isinstance(ai_result, Mapping) or ai_result.get("fallback_used"):
                log_event("AI_FALLBACK", provider_mode="optional", fallback_used=True, duration_ms=duration_ms(started, time.perf_counter()))
                return self._fallback(deterministic, "provider_fallback")
            required = {"summary", "risk_factors", "evidence", "recommended_action", "confidence"}
            provider_metadata = {"deterministic_risk_level", "fallback_used"}
            if not required.issubset(ai_result) or set(ai_result).difference(required | provider_metadata):
                log_event("AI_FALLBACK", provider_mode="optional", fallback_used=True, duration_ms=duration_ms(started, time.perf_counter()))
                return self._fallback(deterministic, "invalid_provider_result")
            if ai_result.get("deterministic_risk_level") != deterministic["risk_assessment"]["risk_level"]:
                log_event("AI_FALLBACK", provider_mode="optional", fallback_used=True, duration_ms=duration_ms(started, time.perf_counter()))
                return self._fallback(deterministic, "risk_tampering_rejected")
            validated = validate_ai_output({key: ai_result[key] for key in required})
        except Exception:
            LOGGER.info("provider_integration_failed")
            log_event("AI_FAILED", provider_mode="optional", fallback_used=True, duration_ms=duration_ms(started, time.perf_counter()), error_type="provider_failure")
            return self._fallback(deterministic, "provider_failure")

        # Copy only validated explanatory fields. Numeric risk fields and the
        # deterministic behavioral evidence remain authoritative.
        result = dict(deterministic)
        result.update(
            {
                "investigation_summary": validated["summary"],
                "key_risk_signals": validated["risk_factors"],
                "ai_evidence": validated["evidence"],
                "ai_recommended_action": validated["recommended_action"],
                "ai_confidence": validated["confidence"],
                "recommended_investigation_action": validated["recommended_action"],
                "provider_used": True,
                "fallback_used": False,
                "investigation_mode": "Optional AI Investigator",
                "provider_status": "success",
            }
        )
        log_event("AI_COMPLETED", provider_mode="optional", fallback_used=False, duration_ms=duration_ms(started, time.perf_counter()))
        return result
