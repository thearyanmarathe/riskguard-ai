from __future__ import annotations

import hashlib
import json
import os
import sqlite3
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from run_demo import EXPECTED_IDS, MANIFEST_PATH, load_manifest, run  # noqa: E402


class DemoTests(unittest.TestCase):
    def test_manifest_exists_and_has_exactly_three_scenarios(self) -> None:
        self.assertTrue(MANIFEST_PATH.exists())
        payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        self.assertEqual(payload["version"], "1.0")
        self.assertEqual(tuple(item["id"] for item in payload["scenarios"]), EXPECTED_IDS)
        self.assertEqual(len(payload["scenarios"]), 3)

    def test_source_rows_and_provenance_are_real_selection_metadata(self) -> None:
        scenarios = load_manifest()
        self.assertEqual([item["source_row_id"] for item in scenarios], [28727, 233005, 215984])
        for item in scenarios:
            self.assertEqual(item["provenance"], "REAL_TRANSACTION_WITH_SYNTHETIC_BEHAVIORAL_CONTEXT")

    def test_all_scenarios_use_authoritative_saved_results(self) -> None:
        results = run()
        self.assertEqual([item["report"]["risk_assessment"]["risk_level"] for item in results], ["LOW", "MEDIUM", "HIGH"])
        self.assertEqual([item["report"]["risk_assessment"]["risk_score"] for item in results], [20.95, 40.13, 95.0])
        self.assertEqual([item["report"]["risk_assessment"]["ml_fraud_probability"] for item in results], [0.01587517, 0.002242215, 0.9999875])
        self.assertEqual([item["report"]["risk_assessment"]["behavioral_rule_points"] for item in results], [20.0, 40.0, 35.0])
        self.assertTrue(all(item["report"]["fallback_used"] for item in results))

    def test_single_scenario_modes_and_invalid_mode(self) -> None:
        self.assertEqual(len(run("low_risk")), 1)
        self.assertEqual(run("medium_risk")[0]["report"]["risk_assessment"]["risk_level"], "MEDIUM")
        self.assertEqual(run("high_risk")[0]["report"]["risk_assessment"]["risk_level"], "HIGH")
        with self.assertRaises(ValueError):
            run("unknown")

    def test_runner_does_not_recalculate_or_persist(self) -> None:
        source = (ROOT / "scripts" / "run_demo.py").read_text(encoding="utf-8")
        self.assertNotIn("60 *", source)
        self.assertNotIn("risk_score =", source)
        database = ROOT / "data" / "riskguard.db"
        before = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
        counts_before = before.execute("SELECT COUNT(*), (SELECT COUNT(*) FROM investigation_events) FROM investigations").fetchone()
        before.close()
        run()
        after = sqlite3.connect(f"file:{database}?mode=ro", uri=True)
        counts_after = after.execute("SELECT COUNT(*), (SELECT COUNT(*) FROM investigation_events) FROM investigations").fetchone()
        after.close()
        self.assertEqual(counts_before, counts_after)

    def test_runner_is_offline_and_has_no_raw_copy_or_secret(self) -> None:
        source = (ROOT / "scripts" / "run_demo.py").read_text(encoding="utf-8").lower()
        self.assertNotIn("requests", source)
        self.assertNotIn("urllib", source)
        self.assertNotIn("openai", source)
        self.assertFalse((ROOT / "demo" / "creditcard.csv").exists())
        for path in (MANIFEST_PATH, ROOT / "scripts" / "run_demo.py"):
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("sk-", text)
            self.assertNotIn("BEGIN PRIVATE KEY", text)

    def test_runner_cli_succeeds_and_invalid_scenario_fails_safely(self) -> None:
        env = os.environ.copy()
        env.pop("AI_PROVIDER_API_KEY", None)
        command = [sys.executable, str(ROOT / "scripts" / "run_demo.py")]
        completed = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, text=True, check=False)
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("Demo validation: PASSED", completed.stdout)
        invalid = subprocess.run(command + ["--scenario", "invalid"], cwd=ROOT, env=env, capture_output=True, text=True, check=False)
        self.assertNotEqual(invalid.returncode, 0)

    def test_repeated_runs_are_deterministic(self) -> None:
        first = [(item["scenario"]["id"], item["report"]["risk_assessment"], item["report"]["triggered_behavioral_rules"]) for item in run()]
        second = [(item["scenario"]["id"], item["report"]["risk_assessment"], item["report"]["triggered_behavioral_rules"]) for item in run()]
        self.assertEqual(first, second)

    def test_raw_csv_hash_is_unchanged_by_demo(self) -> None:
        digest = hashlib.sha256((ROOT / "data" / "raw" / "creditcard.csv").read_bytes()).hexdigest().upper()
        self.assertEqual(digest, "76274B691B16A6C49D3F159C883398E03CCD6D1EE12D9D8EE38F4B4B98551A89")


if __name__ == "__main__":
    unittest.main()
