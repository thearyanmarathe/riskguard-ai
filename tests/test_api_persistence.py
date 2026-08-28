from __future__ import annotations

import tempfile
import os
import unittest
from pathlib import Path

from fastapi.testclient import TestClient

import sys
sys.path.insert(0, str(Path(__file__).parents[1]))
sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

import test_support  # noqa: E402,F401
import api.main as api_main  # noqa: E402
from database import Database  # noqa: E402
from investigation_repository import InvestigationRepository  # noqa: E402


class ApiPersistenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.previous_key = os.environ.get("RISKGUARD_API_KEY")
        os.environ["RISKGUARD_API_KEY"] = "test-api-key"
        self.temp_directory = tempfile.TemporaryDirectory()
        self.previous_repository = api_main.repository
        api_main.repository = InvestigationRepository(Database(Path(self.temp_directory.name) / "api-test.db"))
        self.client = TestClient(api_main.app, headers={"X-API-Key": "test-api-key"})

    def tearDown(self) -> None:
        api_main.repository.database.close()
        api_main.repository = self.previous_repository
        if self.previous_key is None:
            os.environ.pop("RISKGUARD_API_KEY", None)
        else:
            os.environ["RISKGUARD_API_KEY"] = self.previous_key
        self.temp_directory.cleanup()

    def test_post_get_and_list_persist_fallback_result(self) -> None:
        representative = {28727: "LOW", 233005: "MEDIUM", 215984: "HIGH"}
        for source_row_id, risk_level in representative.items():
            response = self.client.post("/investigate", json={"source_row_id": source_row_id})
            self.assertEqual(response.status_code, 200)
            self.assertIsInstance(response.json()["persistence_id"], int)
            self.assertEqual(response.json()["risk_level"], risk_level)

        response = self.client.post("/investigate", json={"source_row_id": 215984})
        self.assertEqual(response.status_code, 200)
        body = response.json()
        persistence_id = body["persistence_id"]
        self.assertIsInstance(persistence_id, int)
        self.assertTrue(body["fallback_used"])
        self.assertEqual((body["risk_score"], body["risk_level"], body["ml_fraud_probability"], body["behavioral_points"]), (95.0, "HIGH", 0.9999875, 35.0))
        event_types = {event["event_type"] for event in api_main.repository.list_events(persistence_id)}
        self.assertEqual(event_types, {"INVESTIGATION_CREATED", "INVESTIGATION_COMPLETED"})

        retrieved = self.client.get(f"/investigations/{persistence_id}")
        self.assertEqual(retrieved.status_code, 200)
        self.assertEqual(retrieved.json(), body)
        listed = self.client.get("/investigations", params={"source_row_id": 215984, "limit": 1})
        self.assertEqual(listed.status_code, 200)
        self.assertEqual(len(listed.json()["investigations"]), 1)

    def test_missing_invalid_and_bounded_ids(self) -> None:
        self.assertEqual(self.client.get("/investigations/9999999").status_code, 404)
        self.assertIn(self.client.get("/investigations/not-an-id").status_code, (404, 422))
        self.assertEqual(self.client.get("/investigations", params={"limit": 101}).status_code, 422)
        self.assertEqual(self.client.get("/investigations", params={"limit": -1}).status_code, 422)

    def test_repeated_posts_create_new_records_and_no_sensitive_fields(self) -> None:
        first = self.client.post("/investigate", json={"source_row_id": 28727}).json()
        second = self.client.post("/investigate", json={"source_row_id": 28727}).json()
        self.assertNotEqual(first["persistence_id"], second["persistence_id"])
        serialized = self.client.get(f"/investigations/{first['persistence_id']}").text
        for forbidden in ("AI_PROVIDER_API_KEY", "data/raw/creditcard.csv", "V1", "prompt", "Traceback"):
            self.assertNotIn(forbidden, serialized)


if __name__ == "__main__":
    unittest.main()
