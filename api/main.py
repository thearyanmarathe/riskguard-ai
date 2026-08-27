"""Thin HTTP service over the existing RiskGuard AI Investigator."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import pandas as pd
from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from ai_investigator import ApplicationInvestigator  # noqa: E402
from api.auth import require_api_key  # noqa: E402
from api.schemas import InvestigationDetails, InvestigationListResponse, InvestigationRequest, InvestigationResponse, TriggeredRule  # noqa: E402
from database import Database  # noqa: E402
from investigation_repository import InvestigationRepository  # noqa: E402


ASSESSMENT_PATH = PROJECT_ROOT / "reports" / "behavioral" / "behavioral_risk_assessments.csv"
MAX_REQUEST_BYTES = 4096
app = FastAPI(title="RiskGuard AI API", version="1.0")
investigator = ApplicationInvestigator()
repository = InvestigationRepository(Database())


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


def _response_from_report(report: dict[str, Any], persistence_id: int | None = None, created_at: str | None = None) -> InvestigationResponse:
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
        persistence_id=persistence_id, created_at=created_at,
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


def _persistence_values(report: dict[str, Any], response: InvestigationResponse) -> dict[str, Any]:
    return {
        "source_row_id": response.source_row_id,
        "amount": response.amount,
        "ml_fraud_probability": response.ml_fraud_probability,
        "behavioral_points": response.behavioral_points,
        "risk_score": response.risk_score,
        "risk_level": response.risk_level,
        "triggered_rules": [rule.model_dump() for rule in response.triggered_rules],
        "investigation_summary": response.investigation.summary,
        "risk_factors": response.investigation.key_risk_signals,
        "evidence": response.investigation.evidence,
        "recommended_action": response.investigation.recommended_action,
        "confidence": response.investigation.confidence,
        "provider_used": response.provider_used,
        "fallback_used": response.fallback_used,
    }


def _response_from_stored(stored: dict[str, Any]) -> InvestigationResponse:
    details = InvestigationDetails(
        summary=stored["investigation_summary"],
        key_risk_signals=stored["risk_factors"],
        evidence=stored["evidence"],
        recommended_action=stored["recommended_action"],
        evidence_boundary=(
            "This deterministic report uses only supplied assessment fields and stored rule explanations. "
            "It does not infer customer history, location, motive, account compromise, or proof of fraud."
        ),
        mode="Optional AI Investigator" if stored["provider_used"] else "Deterministic Investigator",
        confidence=stored["confidence"],
    )
    return InvestigationResponse(
        persistence_id=stored["id"], created_at=stored["created_at"], source_row_id=stored["source_row_id"], amount=stored["amount"],
        ml_fraud_probability=stored["ml_fraud_probability"], behavioral_points=stored["behavioral_points"],
        risk_score=stored["risk_score"], risk_level=stored["risk_level"],
        triggered_rules=[TriggeredRule(**rule) for rule in stored["triggered_rules"]],
        investigation=details, provider_used=stored["provider_used"], fallback_used=stored["fallback_used"],
    )


@app.post("/investigate", response_model=InvestigationResponse, dependencies=[Depends(require_api_key)])
def investigate(request: InvestigationRequest) -> InvestigationResponse:
    record = _assessment_record(request.source_row_id)
    try:
        report = investigator.investigate(record)
        response = _response_from_report(report)
        stored = repository.save_investigation(_persistence_values(report, response))
        return _response_from_report(report, persistence_id=stored["id"], created_at=stored["created_at"])
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Internal application failure.") from exc


@app.get("/investigations/{investigation_id}", response_model=InvestigationResponse, dependencies=[Depends(require_api_key)])
def get_investigation(investigation_id: int) -> InvestigationResponse:
    if not 1 <= investigation_id <= 10_000_000:
        raise HTTPException(status_code=404, detail="Investigation not found.")
    try:
        stored = repository.get_investigation(investigation_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Persistence service unavailable.") from exc
    if stored is None:
        raise HTTPException(status_code=404, detail="Investigation not found.")
    return _response_from_stored(stored)


@app.get("/investigations", response_model=InvestigationListResponse, dependencies=[Depends(require_api_key)])
def list_investigations(
    source_row_id: int | None = Query(default=None, ge=0, le=10_000_000),
    limit: int = Query(default=20, ge=1, le=100),
) -> InvestigationListResponse:
    try:
        records = repository.list_recent(limit=limit, source_row_id=source_row_id)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="Persistence service unavailable.") from exc
    return InvestigationListResponse(investigations=[_response_from_stored(record) for record in records])
