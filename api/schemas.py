"""Pydantic request and response contracts for the RiskGuard API."""

from __future__ import annotations

from pydantic import BaseModel, Field, StrictInt


class InvestigationRequest(BaseModel):
    source_row_id: StrictInt = Field(ge=0, le=10_000_000)

    class Config:
        extra = "forbid"


class TriggeredRule(BaseModel):
    rule_name: str
    triggered: bool
    points: int
    evidence: str


class InvestigationDetails(BaseModel):
    summary: str
    key_risk_signals: list[str]
    evidence: list[str]
    recommended_action: str
    evidence_boundary: str
    mode: str
    confidence: float | None = None


class InvestigationResponse(BaseModel):
    source_row_id: int
    amount: float
    ml_fraud_probability: float
    behavioral_points: float
    risk_score: float
    risk_level: str
    triggered_rules: list[TriggeredRule]
    investigation: InvestigationDetails
    provider_used: bool
    fallback_used: bool
