from __future__ import annotations

import io
import logging
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parents[1]))
sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

import test_support  # noqa: E402,F401
from api import auth  # noqa: E402
from api.main import app  # noqa: E402


class AuthenticationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.previous_key = os.environ.get("RISKGUARD_API_KEY")
        os.environ["RISKGUARD_API_KEY"] = "test-api-key"
        self.client = TestClient(app)

    def tearDown(self) -> None:
        if self.previous_key is None:
            os.environ.pop("RISKGUARD_API_KEY", None)
        else:
            os.environ["RISKGUARD_API_KEY"] = self.previous_key

    def test_health_is_public(self) -> None:
        self.assertEqual(self.client.get("/health").status_code, 200)

    def test_protected_routes_require_correct_key(self) -> None:
        for method, path in (
            ("post", "/investigate"),
            ("get", "/investigations/1"),
            ("get", "/investigations"),
        ):
            with self.subTest(path=path):
                if method == "post":
                    missing = self.client.post(path, json={"source_row_id": 28727})
                    response = self.client.post(path, headers={"X-API-Key": "wrong-key"}, json={"source_row_id": 28727})
                else:
                    missing = self.client.get(path)
                    response = self.client.get(path, headers={"X-API-Key": "wrong-key"})
                self.assertEqual(missing.status_code, 401)
                self.assertEqual(response.status_code, 401)
                self.assertEqual(response.json(), {"detail": "Unauthorized"})

    def test_correct_key_allows_investigation(self) -> None:
        response = self.client.post("/investigate", json={"source_row_id": 28727}, headers={"X-API-Key": "test-api-key"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["risk_level"], "LOW")

    def test_constant_time_comparison_is_used(self) -> None:
        with patch("api.auth.hmac.compare_digest", return_value=True) as comparison:
            auth.require_api_key("test-api-key")
        comparison.assert_called_once_with("test-api-key", "test-api-key")

    def test_key_is_not_in_response_or_logs(self) -> None:
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        logger = logging.getLogger("riskguard")
        logger.addHandler(handler)
        try:
            response = self.client.post("/investigate", json={"source_row_id": 28727}, headers={"X-API-Key": "test-api-key"})
        finally:
            logger.removeHandler(handler)
        self.assertNotIn("test-api-key", response.text)
        self.assertNotIn("test-api-key", stream.getvalue())
        self.assertNotEqual(os.environ.get("AI_PROVIDER_API_KEY"), "test-api-key")

    def test_invalid_request_still_rejected_with_correct_key(self) -> None:
        response = self.client.post("/investigate", json={"source_row_id": -1}, headers={"X-API-Key": "test-api-key"})
        self.assertEqual(response.status_code, 422)


if __name__ == "__main__":
    unittest.main()
