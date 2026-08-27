from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from app import (  # noqa: E402
    REQUIRED_COLUMNS,
    assessment_for_source,
    load_assessments,
    lookup_source_investigation,
    risk_distribution,
    rule_rows,
    summarize_investigations,
)
from database import Database  # noqa: E402
from investigation_repository import InvestigationRepository  # noqa: E402


ASSESSMENTS = ROOT / "reports" / "behavioral" / "behavioral_risk_assessments.csv"


def saved_record(source_row_id: int, score: float, level: str, probability: float, points: float, rules: list[dict]) -> dict:
    return {
        "id": source_row_id, "source_row_id": source_row_id, "amount": 10.0, "ml_fraud_probability": probability,
        "behavioral_points": points, "risk_score": score, "risk_level": level, "triggered_rules": rules,
        "investigation_summary": "Stored summary", "risk_factors": ["Stored signal"], "evidence": ["Stored evidence"],
        "recommended_action": "MANUAL_REVIEW", "confidence": None, "provider_used": False, "fallback_used": True,
        "created_at": "2026-01-01T00:00:00Z",
    }


class DashboardTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.assessments = load_assessments(str(ASSESSMENTS))

    def test_import_and_representative_saved_cases(self) -> None:
        self.assertTrue(REQUIRED_COLUMNS.issubset(self.assessments.columns))
        for source_row_id, expected in ((28727, "LOW"), (233005, "MEDIUM"), (215984, "HIGH")):
            self.assertEqual(assessment_for_source(self.assessments, source_row_id)["risk_level"], expected)

    def test_metrics_and_distribution_use_stored_values(self) -> None:
        records = [saved_record(28727, 20.95, "LOW", 0.01587517, 20, []), saved_record(233005, 40.13, "MEDIUM", 0.002242215, 40, []), saved_record(215984, 95.0, "HIGH", 0.9999875, 35, [])]
        self.assertEqual(summarize_investigations(records), {"total": 3, "HIGH": 1, "MEDIUM": 1, "LOW": 1, "fallback": 3, "provider": 0})
        self.assertEqual(risk_distribution(records)["Investigations"].tolist(), [1, 1, 1])
        self.assertEqual((records[2]["risk_score"], records[2]["ml_fraud_probability"], records[2]["behavioral_points"]), (95.0, 0.9999875, 35))

    def test_behavioral_and_synthetic_context_are_available(self) -> None:
        high = assessment_for_source(self.assessments, 215984)
        deviation = next(row for row in rule_rows(high) if row["Rule"] == "High amount deviation")
        self.assertEqual(deviation["Points"], 20)
        self.assertTrue(deviation["Stored explanation"])
        self.assertIn("historical_average_amount", high)
        self.assertIn("amount_deviation", high)

    def test_empty_repository_and_lookup_are_safe(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = InvestigationRepository(Database(Path(directory) / "dashboard.db"))
            self.assertIsNone(lookup_source_investigation(repository, 28727))
            self.assertEqual(repository.risk_level_counts(), {"LOW": 0, "MEDIUM": 0, "HIGH": 0})
            self.assertEqual(summarize_investigations([])["total"], 0)
            repository.database.close()

    def test_source_has_presentation_boundaries(self) -> None:
        source = (ROOT / "scripts" / "app.py").read_text(encoding="utf-8")
        self.assertIn("SYNTHETIC DEMO BEHAVIORAL METADATA", source)
        self.assertIn("ADVISORY", source)
        self.assertNotIn("risk_score =", source)
        for forbidden in ("AI_PROVIDER_API_KEY=", "shell=True", "openai.ChatCompletion"):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
