"""Minimal application API-key authentication for protected FastAPI routes."""

from __future__ import annotations

import hmac
import os

from fastapi import Header, HTTPException, status

from observability import log_event


API_KEY_ENV = "RISKGUARD_API_KEY"


def require_api_key(x_api_key: str | None = Header(default=None, alias="X-API-Key")) -> None:
    """Require the configured application key without revealing auth details."""
    expected = os.environ.get(API_KEY_ENV, "")
    supplied = x_api_key or ""
    if not expected or not hmac.compare_digest(supplied, expected):
        log_event("AUTHENTICATION_FAILED", status="rejected")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")
