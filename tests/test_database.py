from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from sqlalchemy import inspect

import sys
sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from database import Database  # noqa: E402
from investigation_repository import InvestigationRepository  # noqa: E402


def values(source_row_id: int = 1) -> dict[str, object]:
    return {
        "source_row_id": source_row_id, "amount": 10.0, "ml_fraud_probability": 0.1,
        "behavioral_points": 20.0, "risk_score": 26.0, "risk_level": "MEDIUM",
        "triggered_rules": [{"rule_name": "High amount deviation", "triggered": True, "points": 20, "evidence": "Synthetic rule."}],
        "investigation_summary": "Validated investigation.", "risk_factors": ["Saved signal."],
        "evidence": ["Saved evidence."], "recommended_action": "MANUAL_REVIEW", "confidence": None,
        "provider_used": False, "fallback_used": True,
    }


class DatabaseTests(unittest.TestCase):
    def test_initializes_and_reopens_without_deleting_records(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "riskguard.db"
            database = Database(path)
            repository = InvestigationRepository(database)
            saved = repository.save_investigation(values())
            database.close()
            reopened = Database(path)
            repository_again = InvestigationRepository(reopened)
            self.assertEqual(repository_again.get_investigation(saved["id"])["source_row_id"], 1)
            self.assertIn("investigations", inspect(reopened.engine).get_table_names())
            reopened.close()

    def test_initialization_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Database(Path(directory) / "riskguard.db")
            repository = InvestigationRepository(database)
            repository.save_investigation(values())
            repository.database.initialize()
            self.assertEqual(len(repository.list_recent()), 1)
            database.close()


if __name__ == "__main__":
    unittest.main()
