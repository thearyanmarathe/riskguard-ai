from __future__ import annotations

import io
import json
import logging
import os
import sys
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import test_support  # noqa: E402,F401
import api.main as api_main  # noqa: E402
from observability import duration_ms, log_event, new_request_id  # noqa: E402


class ObservabilityTests(unittest.TestCase):
    def setUp(self) -> None:
        self.previous_app_key = os.environ.get("RISKGUARD_API_KEY")
        self.previous_ai_key = os.environ.get("AI_PROVIDER_API_KEY")
        os.environ["RISKGUARD_API_KEY"] = "test-api-key"
        os.environ.pop("AI_PROVIDER_API_KEY", None)
        self.client = TestClient(api_main.app)
        self.stream = io.StringIO()
        self.handler = logging.StreamHandler(self.stream)
        self.logger = logging.getLogger("riskguard")
        self.logger.addHandler(self.handler)
        self.logger.setLevel(logging.INFO)

    def tearDown(self) -> None:
        self.logger.removeHandler(self.handler)
        if self.previous_app_key is None:
            os.environ.pop("RISKGUARD_API_KEY", None)
        else:
            os.environ["RISKGUARD_API_KEY"] = self.previous_app_key
        if self.previous_ai_key is None:
            os.environ.pop("AI_PROVIDER_API_KEY", None)
        else:
            os.environ["AI_PROVIDER_API_KEY"] = self.previous_ai_key

    def records(self) -> list[dict[str, object]]:
        return [json.loads(line) for line in self.stream.getvalue().splitlines() if line.strip().startswith("{")]

    def test_structured_events_and_nonnegative_timing(self) -> None:
        log_event("TEST_EVENT", status="success", duration_ms=1.25)
        record = self.records()[0]
        self.assertEqual(record["event"], "TEST_EVENT")
        self.assertEqual(record["status"], "success")
        self.assertGreaterEqual(record["duration_ms"], 0)
        self.assertGreaterEqual(duration_ms(10.0, 9.0), 0)

    def test_request_id_header_and_logs_are_safe(self) -> None:
        supplied = str(uuid.uuid4())
        response = self.client.get("/health", headers={"X-Request-ID": supplied})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Request-ID"], supplied)
        events = self.records()
        self.assertTrue(any(event["request_id"] == supplied for event in events))

        generated = self.client.get("/health", headers={"X-Request-ID": "unsafe request id"})
        self.assertNotEqual(generated.headers["X-Request-ID"], "unsafe request id")
        uuid.UUID(generated.headers["X-Request-ID"])

    def test_auth_failure_and_fallback_lifecycle_events(self) -> None:
        rejected = self.client.post("/investigate", json={"source_row_id": 28727}, headers={"X-API-Key": "wrong-key"})
        self.assertEqual(rejected.status_code, 401)
        response = self.client.post("/investigate", json={"source_row_id": 28727}, headers={"X-API-Key": "test-api-key"})
        self.assertEqual(response.status_code, 200)
        events = {event["event"] for event in self.records()}
        self.assertIn("AUTHENTICATION_FAILED", events)
        self.assertIn("INVESTIGATION_STARTED", events)
        self.assertIn("AI_FALLBACK", events)
        self.assertIn("PERSISTENCE_COMPLETED", events)
        self.assertIn("INVESTIGATION_COMPLETED", events)

    def test_logs_do_not_contain_secrets_prompts_or_transaction_details(self) -> None:
        self.client.post(
            "/investigate",
            json={"source_row_id": 28727},
            headers={"X-API-Key": "test-api-key", "X-Request-ID": str(uuid.uuid4())},
        )
        logs = self.stream.getvalue()
        for forbidden in ("test-api-key", "AI_PROVIDER_API_KEY", "X-API-Key", "V1", "Amount", "prompt", "28727"):
            self.assertNotIn(forbidden, logs)

    def test_persistence_failure_and_unexpected_error_are_safe(self) -> None:
        with patch.object(api_main.repository, "save_investigation", side_effect=RuntimeError("secret path should not escape")):
            failed = self.client.post("/investigate", json={"source_row_id": 28727}, headers={"X-API-Key": "test-api-key"})
        self.assertEqual(failed.status_code, 500)
        self.assertEqual(failed.json(), {"detail": "Internal application failure."})
        self.assertIn('"event":"PERSISTENCE_FAILED"', self.stream.getvalue())
        self.assertIn('"error_type":"RuntimeError"', self.stream.getvalue())
        self.assertNotIn("secret path should not escape", self.stream.getvalue())

        original = api_main.investigator.investigate
        try:
            api_main.investigator.investigate = lambda record: (_ for _ in ()).throw(RuntimeError("unexpected secret"))
            failed = self.client.post("/investigate", json={"source_row_id": 28727}, headers={"X-API-Key": "test-api-key"})
        finally:
            api_main.investigator.investigate = original
        self.assertEqual(failed.status_code, 500)
        self.assertNotIn("unexpected secret", failed.text)

    def test_readiness_is_public_and_optional_ai_does_not_affect_it(self) -> None:
        response = self.client.get("/ready")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ready"})
        self.assertEqual(self.client.get("/health").json(), {"status": "ok"})


if __name__ == "__main__":
    unittest.main()
