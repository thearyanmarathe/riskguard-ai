from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parents[1]))

from api.main import app  # noqa: E402


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(app)

    def investigate(self, source_row_id: int):
        return self.client.post("/investigate", json={"source_row_id": source_row_id})

    def test_health(self) -> None:
        response = self.client.get("/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})

    def test_low_medium_high_and_fallback(self) -> None:
        expected = {28727: "LOW", 233005: "MEDIUM", 215984: "HIGH"}
        for source_row_id, level in expected.items():
            with self.subTest(source_row_id=source_row_id):
                response = self.investigate(source_row_id)
                self.assertEqual(response.status_code, 200)
                body = response.json()
                self.assertEqual(body["risk_level"], level)
                self.assertFalse(body["provider_used"])
                self.assertTrue(body["fallback_used"])

    def test_high_amount_deviation_is_visible(self) -> None:
        body = self.investigate(215984).json()
        rule_names = [rule["rule_name"] for rule in body["triggered_rules"]]
        self.assertIn("High amount deviation", rule_names)

    def test_request_validation(self) -> None:
        cases = [
            ({}, 422),
            ({"source_row_id": "215984"}, 422),
            ({"source_row_id": -1}, 422),
            ({"source_row_id": 10_000_001}, 422),
            ({"source_row_id": 215984, "risk_score": 0}, 422),
            ({"source_row_id": 215984, "risk_level": "LOW"}, 422),
        ]
        for payload, status in cases:
            with self.subTest(payload=payload):
                self.assertEqual(self.client.post("/investigate", json=payload).status_code, status)

    def test_malformed_request_and_missing_assessment(self) -> None:
        malformed = self.client.post("/investigate", content="{not-json", headers={"content-type": "application/json"})
        self.assertEqual(malformed.status_code, 422)
        missing = self.investigate(9999999)
        self.assertEqual(missing.status_code, 404)
        self.assertEqual(missing.json(), {"detail": "Saved assessment not found."})

    def test_response_is_allowlisted_and_contains_no_secrets_or_paths(self) -> None:
        response = self.investigate(215984)
        self.assertEqual(response.status_code, 200)
        serialized = json.dumps(response.json())
        self.assertNotIn("AI_PROVIDER_API_KEY", serialized)
        self.assertNotIn("data/raw/creditcard.csv", serialized)
        self.assertNotIn("C:\\ARYAN", serialized)
        self.assertNotIn("risk_score", response.json()["investigation"])


if __name__ == "__main__":
    unittest.main()
