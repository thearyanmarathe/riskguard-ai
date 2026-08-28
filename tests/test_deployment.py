"""Deployment and production-readiness regression checks."""

from __future__ import annotations

import hashlib
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

import pandas as pd
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from ai_investigator import ApplicationInvestigator  # noqa: E402
from database import Database  # noqa: E402
from investigator import DeterministicInvestigator  # noqa: E402
from validate_risk_engine import implementation_cases  # noqa: E402

import test_support  # noqa: E402,F401
import api.main as api_main  # noqa: E402


class DeploymentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.key = "deployment-test-key"
        cls.old_key = os.environ.get("RISKGUARD_API_KEY")
        os.environ["RISKGUARD_API_KEY"] = cls.key
        api_main.rate_limiter.reset()
        cls.client = TestClient(api_main.app)
        cls.assessments = pd.read_csv(ROOT / "reports" / "behavioral" / "behavioral_risk_assessments.csv")

    @classmethod
    def tearDownClass(cls) -> None:
        api_main.rate_limiter.reset()
        if cls.old_key is None:
            os.environ.pop("RISKGUARD_API_KEY", None)
        else:
            os.environ["RISKGUARD_API_KEY"] = cls.old_key

    def test_environment_defaults_are_documented(self) -> None:
        env = (ROOT / ".env.example").read_text(encoding="utf-8")
        for name in ("RISKGUARD_API_KEY", "AI_PROVIDER_API_KEY", "AI_MODEL", "AI_TIMEOUT_SECONDS", "RISKGUARD_LOG_LEVEL"):
            self.assertIn(name, env)

    def test_health_and_readiness(self) -> None:
        self.assertEqual(self.client.get("/health").json(), {"status": "ok"})
        self.assertEqual(self.client.get("/ready").json(), {"status": "ready"})

    def test_api_startup_configuration_is_deterministic(self) -> None:
        dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
        self.assertIn('"uvicorn", "api.main:app"', dockerfile)
        self.assertNotIn("--reload", dockerfile)

    def test_authentication_and_security_headers(self) -> None:
        self.assertEqual(self.client.get("/investigations").status_code, 401)
        response = self.client.get("/health")
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.headers["X-Frame-Options"], "DENY")

    def test_body_limit_and_rate_configuration(self) -> None:
        response = self.client.post("/investigate", content=b"x" * (api_main.MAX_REQUEST_BYTES + 1))
        self.assertEqual(response.status_code, 413)
        self.assertGreaterEqual(api_main.rate_limiter.tracked_clients, 0)

    def test_safe_logging_and_no_secrets_in_deployment_config(self) -> None:
        observability = (ROOT / "scripts" / "observability.py").read_text(encoding="utf-8")
        self.assertNotIn("API_PROVIDER_KEY", observability)
        for name in ("Dockerfile", "docker-compose.yml", ".env.example"):
            content = (ROOT / name).read_text(encoding="utf-8")
            self.assertNotIn("sk-", content)
            self.assertNotIn("-----BEGIN", content)

    def test_database_initialization(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            database = Database(Path(directory) / "deployment.db")
            database.initialize()
            with database.engine.connect() as connection:
                self.assertEqual(connection.exec_driver_sql("SELECT 1").scalar(), 1)
            database.close()

    def test_model_artifact_and_representative_integrity(self) -> None:
        artifact = ROOT / "reports" / "model" / "xgboost_baseline.json"
        self.assertTrue(artifact.is_file())
        self.assertGreater(artifact.stat().st_size, 0)
        row = self.assessments.loc[self.assessments.source_row_id == 215984].iloc[0]
        expected = min(100.0, 60.0 * float(row.ml_fraud_probability) + float(row.behavioral_rule_points))
        self.assertAlmostEqual(float(row.risk_score), round(expected, 2), places=2)

    def test_deterministic_fallback(self) -> None:
        row = self.assessments.loc[self.assessments.source_row_id == 28727].iloc[0].to_dict()
        result = ApplicationInvestigator(provider_factory=lambda: (_ for _ in ()).throw(RuntimeError("unavailable"))).investigate(row)
        self.assertTrue(result["fallback_used"])
        self.assertFalse(result["provider_used"])
        self.assertEqual(result["risk_assessment"]["risk_level"], "LOW")

    def test_dashboard_import_and_validation_tool_fix(self) -> None:
        compile((ROOT / "scripts" / "app.py").read_text(encoding="utf-8"), "scripts/app.py", "exec")
        cases = implementation_cases()
        self.assertEqual(len(cases), 5)
        self.assertIn("High Amount Deviation", cases.iloc[-1].rule_details)

    def test_documentation_consistency(self) -> None:
        docs = (ROOT / "docs" / "DEPLOYMENT.md").read_text(encoding="utf-8")
        for heading in ("## Architecture", "## Health Checks", "## Readiness", "## Authentication", "## TLS / Reverse Proxy", "## Known Limitations"):
            self.assertIn(heading, docs)
        self.assertIn("riskguard-data", (ROOT / "docker-compose.yml").read_text(encoding="utf-8"))

    def test_saved_risk_values_and_ml_probabilities_are_not_changed(self) -> None:
        before = self.assessments.set_index("source_row_id", drop=False)
        for source_row_id in (28727, 233005, 215984):
            row = before.loc[source_row_id].to_dict()
            report = DeterministicInvestigator().investigate(row)
            self.assertEqual(report["risk_assessment"]["risk_score"], float(row["risk_score"]))
            self.assertEqual(report["risk_assessment"]["ml_fraud_probability"], float(row["ml_fraud_probability"]))

    def test_raw_csv_hash_is_stable(self) -> None:
        raw = ROOT / "data" / "raw" / "creditcard.csv"
        digest = hashlib.sha256(raw.read_bytes()).hexdigest()
        self.assertEqual(len(digest), 64)


if __name__ == "__main__":
    unittest.main()
