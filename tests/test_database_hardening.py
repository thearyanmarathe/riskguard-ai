from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError

import sys
sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from database import Database  # noqa: E402
from investigation_repository import InvestigationModel, InvestigationRepository  # noqa: E402
from test_database import values  # noqa: E402


class DatabaseHardeningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.directory.name) / "hardening.db")
        self.repository = InvestigationRepository(self.database)

    def tearDown(self) -> None:
        self.database.close()
        self.directory.cleanup()

    def model_values(self, **updates: object) -> dict[str, object]:
        data = {
            "source_row_id": 1, "amount": 10.0, "ml_fraud_probability": 0.1,
            "behavioral_points": 20.0, "risk_score": 26.0, "risk_level": "MEDIUM",
            "triggered_rules": "[]", "investigation_summary": "summary", "risk_factors": "[]",
            "evidence": "[]", "recommended_action": "MANUAL_REVIEW", "confidence": None,
            "provider_used": False, "fallback_used": True, "created_at": datetime.now(timezone.utc).replace(tzinfo=None),
        }
        data.update(updates)
        return data

    def assert_constraint_rejects(self, field: str, value: object) -> None:
        with self.assertRaises(IntegrityError):
            with self.database.session() as session:
                session.add(InvestigationModel(**self.model_values(**{field: value})))
                session.flush()
        self.assertEqual(len(self.repository.list_recent()), 0)

    def test_database_constraints_reject_invalid_values(self) -> None:
        for field, invalid in (
            ("source_row_id", -1), ("amount", -1.0), ("ml_fraud_probability", 1.1),
            ("behavioral_points", -1.0), ("risk_score", 100.1), ("risk_level", "UNKNOWN"),
            ("confidence", 1.1),
        ):
            with self.subTest(field=field):
                self.assert_constraint_rejects(field, invalid)

    def test_required_columns_reject_null(self) -> None:
        required = ("source_row_id", "amount", "ml_fraud_probability", "behavioral_points", "risk_score", "risk_level", "investigation_summary", "recommended_action", "provider_used", "fallback_used", "created_at")
        for field in required:
            with self.subTest(field=field):
                self.assert_constraint_rejects(field, None)

    def test_indexes_and_sqlite_hardening_exist(self) -> None:
        database_inspector = inspect(self.database.engine)
        indexes = {index["name"] for index in database_inspector.get_indexes("investigations")}
        self.assertIn("ix_investigations_source_created", indexes)
        self.assertIn("ix_investigations_source_row_id", indexes)
        self.assertIn("ix_investigations_created_at", indexes)
        with self.database.engine.connect() as connection:
            self.assertEqual(connection.exec_driver_sql("PRAGMA foreign_keys").scalar(), 1)
            self.assertGreaterEqual(connection.exec_driver_sql("PRAGMA busy_timeout").scalar(), 5000)

    def test_audit_events_reference_saved_record_and_are_append_only(self) -> None:
        saved = self.repository.save_investigation(values(9))
        events = self.repository.list_events(saved["id"])
        self.assertEqual([event["event_type"] for event in reversed(events)], ["INVESTIGATION_CREATED", "INVESTIGATION_COMPLETED"])
        self.assertTrue(all(event["investigation_id"] == saved["id"] for event in events))
        self.assertNotIn("prompt", json.dumps(events).lower())
        self.assertNotIn("api_key", json.dumps(events).lower())

    def test_failed_transaction_leaves_no_record(self) -> None:
        invalid = values(12)
        invalid["risk_score"] = 101.0
        with self.assertRaises(ValueError):
            self.repository.save_investigation(invalid)
        self.assertEqual(self.repository.list_recent(), [])

    def test_oversized_text_is_rejected(self) -> None:
        invalid = values()
        invalid["investigation_summary"] = "x" * 5001
        with self.assertRaises(ValueError):
            self.repository.save_investigation(invalid)


if __name__ == "__main__":
    unittest.main()
