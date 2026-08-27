from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts"))

import api.main as api_main  # noqa: E402
from database import Database  # noqa: E402
from investigation_repository import InvestigationRepository  # noqa: E402


class ApiHardeningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.previous_key = os.environ.get("RISKGUARD_API_KEY")
        self.previous_limit = os.environ.get("RISKGUARD_RATE_LIMIT_REQUESTS")
        self.previous_window = os.environ.get("RISKGUARD_RATE_LIMIT_WINDOW_SECONDS")
        os.environ["RISKGUARD_API_KEY"] = "test-api-key"
        self.temp_directory = tempfile.TemporaryDirectory()
        self.previous_repository = api_main.repository
        api_main.repository = InvestigationRepository(Database(Path(self.temp_directory.name) / "hardening.db"))
        api_main.rate_limiter.reset()
        self.client = TestClient(api_main.app, headers={"X-API-Key": "test-api-key"})

    def tearDown(self) -> None:
        api_main.rate_limiter.reset()
        api_main.repository.database.close()
        api_main.repository = self.previous_repository
        self.temp_directory.cleanup()
        for name, value in (("RISKGUARD_API_KEY", self.previous_key), ("RISKGUARD_RATE_LIMIT_REQUESTS", self.previous_limit), ("RISKGUARD_RATE_LIMIT_WINDOW_SECONDS", self.previous_window)):
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value

    def post(self, payload: object, **kwargs):
        return self.client.post("/investigate", json=payload, **kwargs)

    def test_authentication_variants_and_health_public(self) -> None:
        unauthenticated = TestClient(api_main.app)
        for key in (None, "", " ", "x" * 10_000, "wrong-key"):
            headers = {} if key is None else {"X-API-Key": key}
            self.assertEqual(unauthenticated.post("/investigate", json={"source_row_id": 28727}, headers=headers).status_code, 401)
        self.assertEqual(self.post({"source_row_id": 28727}).status_code, 200)
        self.assertEqual(self.client.get("/health").status_code, 200)

    def test_request_validation_and_body_limit(self) -> None:
        cases = [
            ({}, 422), ({"source_row_id": None}, 422), ({"source_row_id": True}, 422),
            ({"source_row_id": 1.0}, 422), ({"source_row_id": "28727"}, 422),
            ({"source_row_id": -1}, 422), ({"source_row_id": 10_000_001}, 422),
            ({"source_row_id": 28727, "risk_score": 0}, 422),
        ]
        for payload, expected in cases:
            self.assertEqual(self.post(payload).status_code, expected)
        malformed = self.client.post("/investigate", content="{bad", headers={"Content-Type": "application/json"})
        self.assertEqual(malformed.status_code, 422)
        wrong_type = self.client.post("/investigate", content='{"source_row_id":28727}', headers={"Content-Type": "text/plain"})
        self.assertEqual(wrong_type.status_code, 422)
        below = '{"source_row_id":28727}' + (" " * 4060)
        self.assertEqual(self.client.post("/investigate", content=below, headers={"Content-Type": "application/json"}).status_code, 200)
        above = '{"source_row_id":28727}' + (" " * 4080)
        self.assertEqual(self.client.post("/investigate", content=above, headers={"Content-Type": "application/json"}).status_code, 413)

    def test_query_and_path_inputs_are_safe(self) -> None:
        self.assertEqual(self.client.get("/investigations", params={"source_row_id": -1}).status_code, 422)
        self.assertEqual(self.client.get("/investigations", params={"source_row_id": "1 OR 1=1"}).status_code, 422)
        self.assertEqual(self.client.get("/investigations", params={"limit": 101}).status_code, 422)
        self.assertEqual(self.client.get("/investigations", params={"limit": 0}).status_code, 422)
        self.assertEqual(self.client.get("/investigations", params={"limit": "1.5"}).status_code, 422)
        self.assertEqual(self.client.get("/investigations", params={"unexpected": "x"}).status_code, 422)
        for path in ("/investigations/0", "/investigations/-1", "/investigations/1.5", "/investigations/1%20OR%201=1", "/investigations/../etc"):
            self.assertIn(self.client.get(path).status_code, {404, 422})
        self.assertEqual(self.client.get("/investigations/9999999").json(), {"detail": "Investigation not found."})

    def test_headers_request_ids_and_safe_response(self) -> None:
        supplied = str(uuid.uuid4())
        response = self.post({"source_row_id": 28727}, headers={"X-Request-ID": supplied})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["X-Request-ID"], supplied)
        for name, value in (("X-Content-Type-Options", "nosniff"), ("X-Frame-Options", "DENY"), ("Referrer-Policy", "no-referrer")):
            self.assertEqual(response.headers[name], value)
        unsafe = self.client.get("/health", headers={"X-Request-ID": "bad\nrequest"})
        self.assertNotEqual(unsafe.headers["X-Request-ID"], "bad\nrequest")
        uuid.UUID(unsafe.headers["X-Request-ID"])
        serialized = json.dumps(response.json())
        for forbidden in ("test-api-key", "Traceback", "data/raw/creditcard.csv", "V1", "prompt"):
            self.assertNotIn(forbidden, serialized)

    def test_rate_limit_and_expiration(self) -> None:
        os.environ["RISKGUARD_RATE_LIMIT_REQUESTS"] = "2"
        os.environ["RISKGUARD_RATE_LIMIT_WINDOW_SECONDS"] = "1"
        api_main.rate_limiter.reset()
        self.assertEqual(self.post({"source_row_id": 28727}).status_code, 200)
        self.assertEqual(self.post({"source_row_id": 28727}).status_code, 200)
        limited = self.post({"source_row_id": 28727})
        self.assertEqual(limited.status_code, 429)
        self.assertIn("Retry-After", limited.headers)
        with patch("api.rate_limit.time.monotonic", side_effect=[100.0, 102.0]):
            api_main.rate_limiter.reset()
            self.assertEqual(api_main.rate_limiter.check("client"), (True, 0))
            self.assertEqual(api_main.rate_limiter.check("client"), (True, 0))
        self.assertEqual(api_main.rate_limiter.tracked_clients, 1)

    def test_unsupported_methods_do_not_mutate(self) -> None:
        for method in ("put", "patch", "delete"):
            response = getattr(self.client, method)("/investigations/1")
            self.assertEqual(response.status_code, 405)

    def test_safe_unexpected_and_dependency_failures(self) -> None:
        with patch.object(api_main.investigator, "investigate", side_effect=RuntimeError("secret internals")):
            response = self.post({"source_row_id": 28727})
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"detail": "Internal application failure."})
        self.assertNotIn("secret internals", response.text)
        with patch.object(api_main.repository, "get_investigation", side_effect=RuntimeError("db path")):
            response = self.client.get("/investigations/1")
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.json(), {"detail": "Persistence service unavailable."})


if __name__ == "__main__":
    unittest.main()
