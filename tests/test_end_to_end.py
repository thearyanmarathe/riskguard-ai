from __future__ import annotations

import hashlib
import json
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd
from fastapi.testclient import TestClient

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT))

from ai_investigator import ApplicationInvestigator  # noqa: E402
from ai_provider import OpenAIProvider  # noqa: E402
from app import rule_rows  # noqa: E402
from api.main import app  # noqa: E402
from test_ai_provider import FakeResponse, VALID_RESPONSE  # noqa: E402


ASSESSMENT_PATH = ROOT / "reports" / "behavioral" / "behavioral_risk_assessments.csv"
RAW_PATH = ROOT / "data" / "raw" / "creditcard.csv"
MODEL_PATH = ROOT / "reports" / "model" / "xgboost_baseline.json"
EXPLAINABILITY_DIR = ROOT / "reports" / "model" / "explainability"
EXPECTED = {28727: ("LOW", 20.95, 0.01587517), 233005: ("MEDIUM", 40.13, 0.002242215), 215984: ("HIGH", 95.0, 0.9999875)}


def raw_hash() -> str:
    digest = hashlib.sha256()
    with RAW_PATH.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class EndToEndTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.assessments = pd.read_csv(ASSESSMENT_PATH)
        cls.client = TestClient(app)

    def row(self, source_row_id: int) -> dict[str, object]:
        return self.assessments.loc[self.assessments["source_row_id"] == source_row_id].iloc[0].to_dict()

    def test_saved_assessments_and_formula_invariants(self) -> None:
        for source_row_id, (level, score, probability) in EXPECTED.items():
            row = self.row(source_row_id)
            for field in ("ml_fraud_probability", "behavioral_rule_points", "risk_score", "risk_level", "triggered_rules"):
                self.assertIn(field, row)
            # Saved assessments persist risk_score to two decimal places.
            self.assertAlmostEqual(float(row["risk_score"]), min(100.0, 60 * float(row["ml_fraud_probability"]) + float(row["behavioral_rule_points"])), delta=0.01)
            self.assertEqual(str(row["risk_level"]), level)
            self.assertAlmostEqual(float(row["risk_score"]), score, places=2)
            self.assertAlmostEqual(float(row["ml_fraud_probability"]), probability, places=8)

    def test_investigator_fallback_and_reproducibility(self) -> None:
        investigator = ApplicationInvestigator(provider=OpenAIProvider(None))
        first = {source_row_id: investigator.investigate(self.row(source_row_id)) for source_row_id in EXPECTED}
        second = {source_row_id: investigator.investigate(self.row(source_row_id)) for source_row_id in EXPECTED}
        self.assertEqual(first, second)
        for source_row_id, (level, score, probability) in EXPECTED.items():
            result = first[source_row_id]
            self.assertTrue(result["fallback_used"])
            self.assertFalse(result["provider_used"])
            self.assertEqual(result["risk_assessment"]["risk_level"], level)
            self.assertAlmostEqual(result["risk_assessment"]["risk_score"], score, places=2)
            self.assertAlmostEqual(result["risk_assessment"]["ml_fraud_probability"], probability, places=8)
            self.assertTrue(result["evidence_boundary"])
            self.assertIn("synthetic", result["synthetic_demo_context"]["disclaimer"].lower())
        high_rules = first[215984]["triggered_behavioral_rules"]
        self.assertIn("High amount deviation", [rule["rule_name"] for rule in high_rules])

    def test_mock_provider_success_and_unsafe_cases_fallback(self) -> None:
        def valid_opener(request: object, timeout: float) -> FakeResponse:
            return FakeResponse({"output_text": json.dumps(VALID_RESPONSE)})

        valid = ApplicationInvestigator(provider=OpenAIProvider("mock-key", opener=valid_opener)).investigate(self.row(233005))
        self.assertTrue(valid["provider_used"])
        self.assertEqual(valid["risk_assessment"]["risk_level"], "MEDIUM")
        self.assertEqual(valid["risk_assessment"]["risk_score"], 40.13)

        unsafe_outputs = [
            {**VALID_RESPONSE, "risk_score": 0},
            {**VALID_RESPONSE, "risk_level": "LOW"},
            {**VALID_RESPONSE, "recommended_action": "TRANSFER_FUNDS"},
        ]
        for output in unsafe_outputs:
            def unsafe_opener(request: object, timeout: float, output: dict[str, object] = output) -> FakeResponse:
                return FakeResponse({"output_text": json.dumps(output)})

            result = ApplicationInvestigator(provider=OpenAIProvider("mock-key", opener=unsafe_opener)).investigate(self.row(233005))
            self.assertTrue(result["fallback_used"])
            self.assertEqual(result["risk_assessment"]["risk_level"], "MEDIUM")
            self.assertEqual(result["risk_assessment"]["risk_score"], 40.13)

    def test_fastapi_end_to_end_and_input_security(self) -> None:
        self.assertEqual(self.client.get("/health").status_code, 200)
        for source_row_id, (level, score, probability) in EXPECTED.items():
            response = self.client.post("/investigate", json={"source_row_id": source_row_id})
            self.assertEqual(response.status_code, 200)
            body = response.json()
            self.assertEqual((body["risk_level"], body["risk_score"]), (level, score))
            self.assertAlmostEqual(body["ml_fraud_probability"], probability, places=8)
            self.assertTrue(body["fallback_used"])
        for payload in ({}, {"source_row_id": "215984"}, {"source_row_id": -1}, {"source_row_id": 10_000_001}, {"source_row_id": 215984, "risk_score": 0}, {"source_row_id": 215984, "risk_level": "LOW"}):
            self.assertEqual(self.client.post("/investigate", json=payload).status_code, 422)
        self.assertEqual(self.client.post("/investigate", json={"source_row_id": 9_999_999}).status_code, 404)
        malformed = self.client.post("/investigate", content="{bad", headers={"content-type": "application/json"})
        self.assertEqual(malformed.status_code, 422)
        serialized = json.dumps(self.client.post("/investigate", json={"source_row_id": 215984}).json())
        for secret in ("AI_PROVIDER_API_KEY", "data/raw/creditcard.csv", "C:\\ARYAN", "Traceback"):
            self.assertNotIn(secret, serialized)

    def test_dashboard_display_path_and_explainability_outputs(self) -> None:
        high = self.row(215984)
        displayed_rules = rule_rows(high)
        self.assertIn("High amount deviation", [rule["Rule"] for rule in displayed_rules])
        self.assertTrue(all(rule["Stored explanation"] for rule in displayed_rules))
        self.assertIn("AI Investigator", (ROOT / "scripts" / "app.py").read_text(encoding="utf-8"))
        self.assertTrue(MODEL_PATH.exists())
        explanation_json = json.loads((EXPLAINABILITY_DIR / "example_transaction_explanations.json").read_text(encoding="utf-8"))
        self.assertEqual({item["risk_level"] for item in explanation_json}, {"LOW", "MEDIUM", "HIGH"})

    def test_raw_hash_is_stable(self) -> None:
        before = raw_hash()
        with patch.dict(os.environ, {}, clear=True):
            ApplicationInvestigator().investigate(self.row(215984))
        self.assertEqual(before, raw_hash())


if __name__ == "__main__":
    unittest.main()
