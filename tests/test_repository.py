from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from database import Database  # noqa: E402
from investigation_repository import InvestigationRepository  # noqa: E402
from test_database import values  # noqa: E402


class RepositoryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_directory = tempfile.TemporaryDirectory()
        self.database = Database(Path(self.temp_directory.name) / "test.db")
        self.repository = InvestigationRepository(self.database)

    def tearDown(self) -> None:
        self.database.close()
        self.temp_directory.cleanup()

    def test_save_get_by_id_and_source(self) -> None:
        saved = self.repository.save_investigation(values(42))
        found = self.repository.get_investigation(saved["id"])
        self.assertEqual(found["source_row_id"], 42)
        self.assertEqual(found["risk_score"], 26.0)
        self.assertEqual(found["triggered_rules"][0]["points"], 20)
        self.assertEqual(len(self.repository.get_by_source_row_id(42)), 1)

    def test_recent_limit_and_deterministic_filter(self) -> None:
        self.repository.save_investigation(values(1))
        self.repository.save_investigation(values(2))
        self.repository.save_investigation(values(1))
        self.assertEqual(len(self.repository.list_recent(limit=2)), 2)
        filtered = self.repository.list_recent(limit=100, source_row_id=1)
        self.assertEqual(len(filtered), 2)
        self.assertEqual(filtered[0]["id"] > filtered[1]["id"], True)

    def test_unvalidated_fields_are_rejected(self) -> None:
        invalid = values()
        invalid["risk_score"] = float("nan")
        with self.assertRaises(ValueError):
            self.repository.save_investigation(invalid)
        invalid = values()
        invalid["unexpected"] = "not allowed"
        with self.assertRaises(ValueError):
            self.repository.save_investigation(invalid)


if __name__ == "__main__":
    unittest.main()
