"""Repository for validated investigation results; it never recalculates risk."""

from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from typing import Any, Mapping

from sqlalchemy import CheckConstraint, DateTime, Float, ForeignKey, Index, Integer, String, Text, desc, select
from sqlalchemy.orm import Mapped, mapped_column

from database import Base, Database


class InvestigationModel(Base):
    __tablename__ = "investigations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_row_id: Mapped[int] = mapped_column(Integer, index=True, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    ml_fraud_probability: Mapped[float] = mapped_column(Float, nullable=False)
    behavioral_points: Mapped[float] = mapped_column(Float, nullable=False)
    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_level: Mapped[str] = mapped_column(String(16), nullable=False)
    triggered_rules: Mapped[str] = mapped_column(Text, nullable=False)
    investigation_summary: Mapped[str] = mapped_column(Text, nullable=False)
    risk_factors: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[str] = mapped_column(Text, nullable=False)
    recommended_action: Mapped[str] = mapped_column(String(64), nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    provider_used: Mapped[bool] = mapped_column(nullable=False)
    fallback_used: Mapped[bool] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    __table_args__ = (
        CheckConstraint("source_row_id >= 0 AND source_row_id <= 10000000", name="ck_investigation_source_row_id"),
        CheckConstraint("amount >= 0", name="ck_investigation_amount"),
        CheckConstraint("ml_fraud_probability >= 0 AND ml_fraud_probability <= 1", name="ck_investigation_ml_probability"),
        CheckConstraint("behavioral_points >= 0", name="ck_investigation_behavioral_points"),
        CheckConstraint("risk_score >= 0 AND risk_score <= 100", name="ck_investigation_risk_score"),
        CheckConstraint("risk_level IN ('LOW', 'MEDIUM', 'HIGH')", name="ck_investigation_risk_level"),
        CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="ck_investigation_confidence"),
        Index("ix_investigations_source_created", "source_row_id", desc("created_at"), desc("id")),
    )


class InvestigationEventModel(Base):
    __tablename__ = "investigation_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    investigation_id: Mapped[int] = mapped_column(ForeignKey("investigations.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    metadata_json: Mapped[str] = mapped_column("metadata", Text, nullable=False, default="{}")
    __table_args__ = (
        CheckConstraint("event_type IN ('INVESTIGATION_CREATED', 'INVESTIGATION_COMPLETED', 'AI_FALLBACK', 'PERSISTENCE_FAILED')", name="ck_investigation_event_type"),
        Index("ix_events_investigation_created", "investigation_id", desc("created_at"), desc("id")),
    )


ALLOWED_FIELDS = {
    "source_row_id", "amount", "ml_fraud_probability", "behavioral_points", "risk_score", "risk_level",
    "triggered_rules", "investigation_summary", "risk_factors", "evidence", "recommended_action",
    "confidence", "provider_used", "fallback_used",
}
LIST_FIELDS = {"triggered_rules", "risk_factors", "evidence"}
ALLOWED_EVENT_TYPES = {"INVESTIGATION_CREATED", "INVESTIGATION_COMPLETED", "AI_FALLBACK", "PERSISTENCE_FAILED"}


def _finite_number(value: Any, field: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"Invalid {field}")
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"Invalid {field}") from error
    if not math.isfinite(number):
        raise ValueError(f"Invalid {field}")
    return number


def _json_list(value: Any, field: str) -> str:
    if not isinstance(value, list) or len(value) > 50:
        raise ValueError(f"Invalid {field}")
    if field == "triggered_rules":
        cleaned = []
        for item in value:
            if not isinstance(item, Mapping) or set(item) != {"rule_name", "triggered", "points", "evidence"}:
                raise ValueError("Invalid triggered_rules")
            if not isinstance(item["rule_name"], str) or len(item["rule_name"]) > 200 or not isinstance(item["evidence"], str) or len(item["evidence"]) > 1000 or not isinstance(item["triggered"], bool):
                raise ValueError("Invalid triggered_rules")
            points = _finite_number(item["points"], "rule points")
            cleaned.append({"rule_name": item["rule_name"], "triggered": item["triggered"], "points": int(points), "evidence": item["evidence"]})
    else:
        if not all(isinstance(item, str) and len(item) <= 1000 for item in value):
            raise ValueError(f"Invalid {field}")
        cleaned = value
    return json.dumps(cleaned, ensure_ascii=False, separators=(",", ":"))


class InvestigationRepository:
    def __init__(self, database: Database) -> None:
        self.database = database
        self.database.initialize()

    def save_investigation(self, values: Mapping[str, Any]) -> dict[str, Any]:
        if set(values) != ALLOWED_FIELDS:
            raise ValueError("Investigation fields are not allowlisted")
        source_row_id = values["source_row_id"]
        if not isinstance(source_row_id, int) or isinstance(source_row_id, bool) or not 0 <= source_row_id <= 10_000_000:
            raise ValueError("Invalid source_row_id")
        risk_level = values["risk_level"]
        if risk_level not in {"LOW", "MEDIUM", "HIGH"}:
            raise ValueError("Invalid risk level")
        if not isinstance(values["investigation_summary"], str) or len(values["investigation_summary"]) > 5000 or not isinstance(values["recommended_action"], str) or len(values["recommended_action"]) > 100:
            raise ValueError("Invalid investigation text")
        if not isinstance(values["provider_used"], bool) or not isinstance(values["fallback_used"], bool):
            raise ValueError("Invalid provider flags")
        confidence = values["confidence"]
        confidence_value = None if confidence is None else _finite_number(confidence, "confidence")
        if confidence_value is not None and not 0 <= confidence_value <= 1:
            raise ValueError("Invalid confidence")
        amount = _finite_number(values["amount"], "amount")
        probability = _finite_number(values["ml_fraud_probability"], "ML probability")
        behavioral_points = _finite_number(values["behavioral_points"], "behavioral points")
        risk_score = _finite_number(values["risk_score"], "risk score")
        if amount < 0 or probability < 0 or probability > 1 or behavioral_points < 0 or risk_score < 0 or risk_score > 100:
            raise ValueError("Investigation numeric value is outside its allowed range")
        record = InvestigationModel(
            source_row_id=source_row_id,
            amount=amount,
            ml_fraud_probability=probability,
            behavioral_points=behavioral_points,
            risk_score=risk_score,
            risk_level=risk_level,
            triggered_rules=_json_list(values["triggered_rules"], "triggered_rules"),
            investigation_summary=values["investigation_summary"],
            risk_factors=_json_list(values["risk_factors"], "risk_factors"),
            evidence=_json_list(values["evidence"], "evidence"),
            recommended_action=values["recommended_action"],
            confidence=confidence_value,
            provider_used=bool(values["provider_used"]),
            fallback_used=bool(values["fallback_used"]),
            created_at=datetime.now(timezone.utc).replace(tzinfo=None),
        )
        with self.database.session() as session:
            session.add(record)
            session.flush()
            metadata = {"provider_used": bool(values["provider_used"]), "fallback_used": bool(values["fallback_used"])}
            session.add(InvestigationEventModel(
                investigation_id=record.id, event_type="INVESTIGATION_CREATED",
                created_at=record.created_at, metadata_json=json.dumps(metadata, sort_keys=True, separators=(",", ":")),
            ))
            session.add(InvestigationEventModel(
                investigation_id=record.id, event_type="INVESTIGATION_COMPLETED",
                created_at=record.created_at, metadata_json=json.dumps(metadata, sort_keys=True, separators=(",", ":")),
            ))
            return self._to_dict(record)

    def get_investigation(self, investigation_id: int) -> dict[str, Any] | None:
        with self.database.session() as session:
            record = session.get(InvestigationModel, investigation_id)
            return self._to_dict(record) if record else None

    def get_by_source_row_id(self, source_row_id: int) -> list[dict[str, Any]]:
        with self.database.session() as session:
            records = session.scalars(select(InvestigationModel).where(InvestigationModel.source_row_id == source_row_id).order_by(desc(InvestigationModel.created_at), desc(InvestigationModel.id))).all()
            return [self._to_dict(record) for record in records]

    def list_recent(self, limit: int = 20, source_row_id: int | None = None) -> list[dict[str, Any]]:
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 100:
            raise ValueError("Invalid limit")
        if source_row_id is not None and (not isinstance(source_row_id, int) or isinstance(source_row_id, bool) or not 0 <= source_row_id <= 10_000_000):
            raise ValueError("Invalid source_row_id")
        with self.database.session() as session:
            query = select(InvestigationModel)
            if source_row_id is not None:
                query = query.where(InvestigationModel.source_row_id == source_row_id)
            records = session.scalars(query.order_by(desc(InvestigationModel.created_at), desc(InvestigationModel.id)).limit(limit)).all()
            return [self._to_dict(record) for record in records]

    def list_events(self, investigation_id: int) -> list[dict[str, Any]]:
        if not isinstance(investigation_id, int) or isinstance(investigation_id, bool) or investigation_id <= 0:
            raise ValueError("Invalid investigation_id")
        with self.database.session() as session:
            events = session.scalars(select(InvestigationEventModel).where(InvestigationEventModel.investigation_id == investigation_id).order_by(desc(InvestigationEventModel.created_at), desc(InvestigationEventModel.id))).all()
            return [{"id": event.id, "investigation_id": event.investigation_id, "event_type": event.event_type, "created_at": event.created_at.isoformat() + "Z", "metadata": json.loads(event.metadata_json)} for event in events]

    @staticmethod
    def _to_dict(record: InvestigationModel) -> dict[str, Any]:
        if record is None:
            return {}
        return {
            "id": record.id,
            "source_row_id": record.source_row_id,
            "amount": record.amount,
            "ml_fraud_probability": record.ml_fraud_probability,
            "behavioral_points": record.behavioral_points,
            "risk_score": record.risk_score,
            "risk_level": record.risk_level,
            "triggered_rules": json.loads(record.triggered_rules),
            "investigation_summary": record.investigation_summary,
            "risk_factors": json.loads(record.risk_factors),
            "evidence": json.loads(record.evidence),
            "recommended_action": record.recommended_action,
            "confidence": record.confidence,
            "provider_used": record.provider_used,
            "fallback_used": record.fallback_used,
            "created_at": record.created_at.isoformat() + "Z",
        }
