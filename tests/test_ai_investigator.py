from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

import pandas as pd
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parents[1] / "scripts"))

from ai_investigator import ApplicationInvestigator  # noqa: E402
from ai_provider import OpenAIProvider  # noqa: E402
from app import rule_rows  # noqa: E402
from test_ai_guardrails import record  # noqa: E402
from test_ai_provider import FakeResponse, VALID_RESPONSE  # noqa: E402


class ApplicationInvestigatorTests(unittest.TestCase):
    def test_missing_key_uses_deterministic_report(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            result = ApplicationInvestigator().investigate(record())
        self.assertFalse(result["provider_used"])
        self.assertTrue(result["fallback_used"])
        self.assertEqual(result["risk_assessment"]["risk_score"], 26.0)
        self.assertEqual(result["risk_assessment"]["risk_level"], "MEDIUM")

    def test_valid_provider_preserves_authoritative_values(self) -> None:
        def opener(request: object, timeout: float) -> FakeResponse:
            return FakeResponse({"output_text": json.dumps(VALID_RESPONSE)})

        result = ApplicationInvestigator(provider=OpenAIProvider("integration-test-key", opener=opener)).investigate(record())
        self.assertTrue(result["provider_used"])
        self.assertFalse(result["fallback_used"])
        self.assertEqual(result["risk_assessment"]["risk_score"], 26.0)
        self.assertEqual(result["risk_assessment"]["risk_level"], "MEDIUM")
        self.assertEqual(result["triggered_behavioral_rules"][0]["rule_name"], "High amount deviation")

    def test_provider_failure_falls_back(self) -> None:
        def timeout(*args: object, **kwargs: object) -> None:
            raise TimeoutError()

        result = ApplicationInvestigator(provider=OpenAIProvider("integration-test-key", opener=timeout)).investigate(record())
        self.assertFalse(result["provider_used"])
        self.assertTrue(result["fallback_used"])
        self.assertEqual(result["risk_assessment"]["risk_score"], 26.0)

    def test_injected_provider_tampering_is_rejected(self) -> None:
        class TamperingProvider:
            api_key = "configured"

            def investigate(self, supplied_record: object) -> dict[str, object]:
                return {**VALID_RESPONSE, "risk_score": 0}

        result = ApplicationInvestigator(provider=TamperingProvider()).investigate(record())
        self.assertFalse(result["provider_used"])
        self.assertEqual(result["provider_status"], "invalid_provider_result")
        self.assertEqual(result["risk_assessment"]["risk_score"], 26.0)

    def test_saved_levels_and_amount_deviation_are_preserved(self) -> None:
        path = Path(__file__).parents[1] / "reports" / "behavioral" / "behavioral_risk_assessments.csv"
        assessments = pd.read_csv(path)
        expected = {28727: "LOW", 233005: "MEDIUM", 215984: "HIGH"}
        investigator = ApplicationInvestigator(provider=OpenAIProvider(None))
        for source_row_id, level in expected.items():
            row = assessments.loc[assessments["source_row_id"] == source_row_id].iloc[0].to_dict()
            result = investigator.investigate(row)
            self.assertEqual(result["risk_assessment"]["risk_level"], level)
            self.assertEqual(result["risk_assessment"]["risk_score"], float(row["risk_score"]))
        high = assessments.loc[assessments["source_row_id"] == 215984].iloc[0].to_dict()
        self.assertTrue(any(rule["rule_name"] == "High amount deviation" for rule in investigator.investigate(high)["triggered_behavioral_rules"]))

    def test_dashboard_rule_display_uses_saved_trigger_and_points(self) -> None:
        path = Path(__file__).parents[1] / "reports" / "behavioral" / "behavioral_risk_assessments.csv"
        high = pd.read_csv(path).loc[lambda frame: frame["source_row_id"] == 215984].iloc[0].to_dict()
        deviation = next(row for row in rule_rows(high) if row["Rule"] == "High amount deviation")
        self.assertEqual(deviation["Triggered"], "Yes")
        self.assertEqual(deviation["Points"], 20)
        self.assertTrue(deviation["Stored explanation"])


if __name__ == "__main__":
    unittest.main()
