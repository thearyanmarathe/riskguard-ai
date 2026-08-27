"""Thin HTTP service over the existing RiskGuard AI Investigator."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from ai_investigator import ApplicationInvestigator  # noqa: E402
from api.schemas import InvestigationRequest, InvestigationResponse, InvestigationDetails, TriggeredRule  # noqa: E402


ASSESSMENT_PATH = PROJECT_ROOT / "reports" / "behavioral" / "behavioral_risk_assessments.csv"
MAX_REQUEST_BYTES = 4096
app = FastAPI(title="RiskGuard AI API", version="1.0")
investigator = ApplicationInvestigator()


@app.middleware("http")
async def request_size_limit(request: Request, call_next: Any) -> JSONResponse:
    content_length = request.headers.get("content-length")
    if content_length:
        try:
            if int(content_length) > MAX_REQUEST_BYTES:
                return JSONResponse(status_code=413, content={"detail": "Request body is too large."})
        except ValueError:
            return JSONResponse(status_code=400, content={"detail": "Invalid request body."})
    return await call_next(request)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": "Invalid request."})


@app.exception_handler(Exception)
async def internal_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"detail": "Internal application failure."})


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


def _assessment_record(source_row_id: int) -> dict[str, Any]:
    try:
        assessments = pd.read_csv(ASSESSMENT_PATH)
        matches = assessments.loc[assessments["source_row_id"] == source_row_id]
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Assessment service unavailable.") from exc
    if matches.empty:
        raise HTTPException(status_code=404, detail="Saved assessment not found.")
    return matches.iloc[0].to_dict()


@app.post("/investigate", response_model=InvestigationResponse)
def investigate(request: InvestigationRequest) -> InvestigationResponse:
    record = _assessment_record(request.source_row_id)
    try:
        report = investigator.investigate(record)
        risk = report["risk_assessment"]
        rules = [TriggeredRule(**rule) for rule in report["triggered_behavioral_rules"]]
        ai_evidence = report.get("ai_evidence")
        evidence = list(ai_evidence) if report.get("provider_used") and ai_evidence else [rule.evidence for rule in rules]
        details = InvestigationDetails(
            summary=report["investigation_summary"],
            key_risk_signals=report["key_risk_signals"],
            evidence=evidence,
            recommended_action=report["recommended_investigation_action"],
            evidence_boundary=report["evidence_boundary"],
            mode=report.get("investigation_mode", "Deterministic Investigator"),
            confidence=report.get("ai_confidence"),
        )
        return InvestigationResponse(
            source_row_id=report["transaction"]["source_row_id"],
            amount=report["transaction"]["amount"],
            ml_fraud_probability=risk["ml_fraud_probability"],
            behavioral_points=risk["behavioral_rule_points"],
            risk_score=risk["risk_score"],
            risk_level=risk["risk_level"],
            triggered_rules=rules,
            investigation=details,
            provider_used=bool(report.get("provider_used", False)),
            fallback_used=bool(report.get("fallback_used", True)),
        )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Internal application failure.") from exc
