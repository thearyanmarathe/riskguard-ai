"""Small, safe structured logging helpers for the local RiskGuard service."""

from __future__ import annotations

import json
import logging
import os
import uuid
from contextvars import ContextVar
from datetime import datetime, timezone
from typing import Any


LOGGER = logging.getLogger("riskguard")
REQUEST_ID: ContextVar[str | None] = ContextVar("riskguard_request_id", default=None)
ALLOWED_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}
SAFE_FIELDS = {"endpoint", "status", "duration_ms", "provider_mode", "fallback_used", "error_type", "model_name"}


def configure_logging() -> None:
    level = os.environ.get("RISKGUARD_LOG_LEVEL", "INFO").upper()
    LOGGER.setLevel(getattr(logging, level if level in ALLOWED_LEVELS else "INFO"))


def new_request_id(candidate: str | None = None) -> str:
    """Accept only canonical UUID input; otherwise generate a safe UUID."""
    if isinstance(candidate, str):
        try:
            parsed = uuid.UUID(candidate)
            return str(parsed)
        except (ValueError, AttributeError):
            pass
    return str(uuid.uuid4())


def set_request_id(request_id: str):
    return REQUEST_ID.set(request_id)


def reset_request_id(token: Any) -> None:
    REQUEST_ID.reset(token)


def current_request_id() -> str | None:
    return REQUEST_ID.get()


def duration_ms(start: float, end: float) -> float:
    return round(max(0.0, (end - start) * 1000), 3)


def log_event(event: str, level: int = logging.INFO, **fields: Any) -> None:
    """Emit one JSON event using only explicitly safe operational fields."""
    payload: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "event": event,
    }
    request_id = current_request_id()
    if request_id:
        payload["request_id"] = request_id
    for key in SAFE_FIELDS:
        value = fields.get(key)
        if value is None:
            continue
        if key == "duration_ms":
            try:
                value = round(max(0.0, float(value)), 3)
            except (TypeError, ValueError):
                continue
        elif key == "fallback_used":
            if not isinstance(value, bool):
                continue
        elif not isinstance(value, str):
            continue
        payload[key] = value
    LOGGER.log(level, json.dumps(payload, sort_keys=True, separators=(",", ":")))


configure_logging()
