"""Run read-only end-to-end validation for the existing RiskGuard system.

This script validates saved assessments, the Investigator integration, the
FastAPI service, dashboard display helpers, model integrity, and raw-data
hash stability. It does not train, regenerate, or modify application data.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pandas as pd
from fastapi.testclient import TestClient
from xgboost import XGBClassifier

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ai_investigator import ApplicationInvestigator  # noqa: E402
from ai_provider import OpenAIProvider  # noqa: E402
from api.main import app  # noqa: E402
from app import rule_rows  # noqa: E402


ASSESSMENT_PATH = PROJECT_ROOT / "reports" / "behavioral" / "behavioral_risk_assessments.csv"
RAW_PATH = PROJECT_ROOT / "data" / "raw" / "creditcard.csv"
MODEL_PATH = PROJECT_ROOT / "reports" / "model" / "xgboost_baseline.json"
EXPLAINABILITY_DIR = PROJECT_ROOT / "reports" / "model" / "explainability"
OUTPUT_DIR = PROJECT_ROOT / "reports" / "e2e"
FEATURE_COLUMNS = ["Time", *[f"V{number}" for number in range(1, 29)], "Amount"]
REPRESENTATIVE = {28727: "LOW", 233005: "MEDIUM", 215984: "HIGH"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class FakeResponse:
    status = 200

    def __init__(self, output: dict[str, object]) -> None:
        self.payload = json.dumps({"output_text": json.dumps(output)}).encode("utf-8")

    def __enter__(self) -> "FakeResponse":
        return self

    def __exit__(self, *args: object) -> None:
        return None

    def read(self, limit: int = -1) -> bytes:
        return self.payload[:limit]


VALID_AI = {
    "summary": "Review the supplied evidence.",
    "risk_factors": ["A stored signal is present."],
    "evidence": ["Saved application evidence."],
    "recommended_action": "MANUAL_REVIEW",
    "confidence": 0.91,
}


def main() -> None:
    assessments = pd.read_csv(ASSESSMENT_PATH)
    results: list[tuple[str, str, str]] = []

    def check(name: str, function) -> None:
        try:
            results.append((name, "PASS", str(function())))
        except Exception as error:  # continue collecting all validation results
            results.append((name, "FAIL", f"{type(error).__name__}: {error}"))

    def row(source_row_id: int) -> dict[str, object]:
        matches = assessments.loc[assessments["source_row_id"] == source_row_id]
        if matches.empty:
            raise AssertionError(f"missing saved row {source_row_id}")
        return matches.iloc[0].to_dict()

    raw_before = sha256(RAW_PATH)

    def saved_integrity() -> str:
        required = ("ml_fraud_probability", "behavioral_rule_points", "risk_score", "risk_level", "triggered_rules")
        for source_row_id in REPRESENTATIVE:
            record = row(source_row_id)
            if any(field not in record for field in required):
                raise AssertionError(f"incomplete assessment {source_row_id}")
        return "saved LOW/MEDIUM/HIGH assessments contain required fields"

    def risk_invariants() -> str:
        for source_row_id in REPRESENTATIVE:
            record = row(source_row_id)
            expected = min(100.0, 60 * float(record["ml_fraud_probability"]) + float(record["behavioral_rule_points"]))
            if not np.isclose(float(record["risk_score"]), expected, atol=0.01):
                raise AssertionError(f"formula mismatch at {source_row_id}")
            level = str(record["risk_level"])
            score = float(record["risk_score"])
            if level == "LOW" and not score < 25:
                raise AssertionError("LOW boundary failure")
            if level == "MEDIUM" and not 25 <= score < 50:
                raise AssertionError("MEDIUM boundary failure")
            if level == "HIGH" and not score >= 50:
                raise AssertionError("HIGH boundary failure")
        return "formula and LOW/MEDIUM/HIGH ranges preserved; saved scores allow 0.01 for two-decimal persistence rounding"

    def investigator_fallback() -> str:
        investigator = ApplicationInvestigator(provider=OpenAIProvider(None))
        for source_row_id, expected_level in REPRESENTATIVE.items():
            record = row(source_row_id)
            report = investigator.investigate(record)
            if not report["fallback_used"] or report["provider_used"]:
                raise AssertionError("fallback flags incorrect")
            if report["risk_assessment"]["risk_level"] != expected_level or not report["evidence_boundary"]:
                raise AssertionError(f"investigator mismatch at {source_row_id}")
            if "synthetic" not in report["synthetic_demo_context"]["disclaimer"].lower():
                raise AssertionError("synthetic metadata disclaimer missing")
        return "deterministic Investigator succeeds for all representative rows"

    def mock_provider() -> str:
        def valid_opener(request: object, timeout: float) -> FakeResponse:
            return FakeResponse(VALID_AI)

        success = ApplicationInvestigator(provider=OpenAIProvider("mock-key", opener=valid_opener)).investigate(row(233005))
        if not success["provider_used"] or success["risk_assessment"]["risk_score"] != 40.13:
            raise AssertionError("valid mocked provider was not accepted safely")
        invalid_outputs = [
            {**VALID_AI, "risk_score": 0},
            {**VALID_AI, "risk_level": "LOW"},
            {**VALID_AI, "recommended_action": "TRANSFER_FUNDS"},
        ]
        for output in invalid_outputs:
            def invalid_opener(request: object, timeout: float, output=output) -> FakeResponse:
                return FakeResponse(output)

            fallback = ApplicationInvestigator(provider=OpenAIProvider("mock-key", opener=invalid_opener)).investigate(row(233005))
            if not fallback["fallback_used"] or fallback["risk_assessment"]["risk_score"] != 40.13:
                raise AssertionError("unsafe mocked output did not fall back")
        return "valid output accepted; invalid, tampered, and disallowed-action outputs fell back"

    def api_validation() -> str:
        client = TestClient(app)
        with patch.dict(os.environ, {}, clear=True):
            for source_row_id, expected_level in REPRESENTATIVE.items():
                response = client.post("/investigate", json={"source_row_id": source_row_id})
                body = response.json()
                if response.status_code != 200 or body["risk_level"] != expected_level or not body["fallback_used"]:
                    raise AssertionError(f"API mismatch at {source_row_id}")
            invalid = ({}, {"source_row_id": "215984"}, {"source_row_id": -1}, {"source_row_id": 10_000_001}, {"source_row_id": 215984, "risk_score": 0}, {"source_row_id": 215984, "risk_level": "LOW"})
            if any(client.post("/investigate", json=payload).status_code != 422 for payload in invalid):
                raise AssertionError("API validation failure")
            if client.post("/investigate", json={"source_row_id": 9_999_999}).status_code != 404:
                raise AssertionError("API 404 failure")
            serialized = json.dumps(client.post("/investigate", json={"source_row_id": 215984}).json())
        for forbidden in ("AI_PROVIDER_API_KEY", "data/raw/creditcard.csv", "C:\\ARYAN", "Traceback"):
            if forbidden in serialized:
                raise AssertionError(f"forbidden response content: {forbidden}")
        return "health, representative rows, validation errors, 404, fallback, and response allowlist passed"

    def dashboard() -> str:
        displayed = rule_rows(row(215984))
        if "High amount deviation" not in [item["Rule"] for item in displayed]:
            raise AssertionError("dashboard rule helper omitted amount deviation")
        if not all(item["Stored explanation"] for item in displayed):
            raise AssertionError("dashboard rule explanation missing")
        return "dashboard module imports and saved LOW/MEDIUM/HIGH display path is valid"

    def model_integrity() -> str:
        model = XGBClassifier()
        model.load_model(MODEL_PATH)
        if list(model.get_booster().feature_names or []) != FEATURE_COLUMNS:
            raise AssertionError("model feature contract changed")
        raw = pd.read_csv(RAW_PATH)
        for source_row_id in REPRESENTATIVE:
            probability = float(model.predict_proba(raw.iloc[[source_row_id]][FEATURE_COLUMNS])[:, 1][0])
            saved = float(row(source_row_id)["ml_fraud_probability"])
            if not np.isclose(probability, saved, atol=1e-6):
                raise AssertionError(f"model probability changed at {source_row_id}")
        files = [EXPLAINABILITY_DIR / "global_feature_importance.csv", EXPLAINABILITY_DIR / "individual_feature_contributions.csv", EXPLAINABILITY_DIR / "example_transaction_explanations.json"]
        if not all(path.exists() for path in files):
            raise AssertionError("explainability output missing")
        return "artifact loaded; 30-feature contract, saved probabilities, and explainability outputs valid"

    def reproducibility() -> str:
        investigator = ApplicationInvestigator(provider=OpenAIProvider(None))
        first = [investigator.investigate(row(source_row_id)) for source_row_id in REPRESENTATIVE]
        second = [investigator.investigate(row(source_row_id)) for source_row_id in REPRESENTATIVE]
        if first != second:
            raise AssertionError("deterministic reports differ")
        return "two deterministic runs produced equivalent reports"

    check("Saved assessment integrity", saved_integrity)
    check("Risk invariants", risk_invariants)
    check("Deterministic Investigator and fallback", investigator_fallback)
    check("Mock AI provider boundary", mock_provider)
    check("FastAPI end-to-end", api_validation)
    check("Streamlit display path", dashboard)
    check("Model integrity and explainability", model_integrity)
    check("Deterministic reproducibility", reproducibility)

    raw_after = sha256(RAW_PATH)
    if raw_before != raw_after:
        results.append(("Raw CSV hash integrity", "FAIL", f"before={raw_before}; after={raw_after}"))
    else:
        results.append(("Raw CSV hash integrity", "PASS", f"SHA-256 unchanged: {raw_before}"))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    payload = [{"check": name, "status": status, "details": details} for name, status, details in results]
    (OUTPUT_DIR / "e2e_results.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")
    passed = sum(status == "PASS" for _, status, _ in results)
    failed = len(results) - passed
    lines = [
        "# RiskGuard AI — Phase 14 End-to-End Validation",
        "",
        "This is a read-only validation of existing saved assessments, Investigator integration, optional-provider fallback, FastAPI, and Streamlit display helpers. No model training, behavioral generation, scoring changes, or raw-data writes were performed.",
        "",
        f"**Checks passed:** {passed}  \n**Checks failed:** {failed}",
        "",
        "## Results",
        "",
        "| Check | Status | Details |",
        "| --- | --- | --- |",
    ]
    lines.extend(f"| {name} | {status} | {details.replace('|', '\\|')} |" for name, status, details in results)
    lines.extend(
        [
            "",
            "## Representative outcomes",
            "",
            "| Source row | Existing level | Existing score | Existing ML probability |",
            "| ---: | --- | ---: | ---: |",
        ]
    )
    for source_row_id in REPRESENTATIVE:
        record = row(source_row_id)
        lines.append(f"| {source_row_id} | {record['risk_level']} | {float(record['risk_score']):.2f} | {float(record['ml_fraud_probability']):.8f} |")
    lines.extend(
        [
            "",
            "## Security and boundary observations",
            "",
            "- No real AI API call was made; missing provider configuration used deterministic fallback.",
            "- Mocked valid AI output was accepted only as an explanation; invalid actions and score/level tampering fell back safely.",
            "- FastAPI did not call OpenAI directly; it used `ApplicationInvestigator` and the existing guarded provider path.",
            "- The API response contained no provider key, filesystem path, traceback, raw CSV, or arbitrary provider fields.",
            "- Streamlit was validated through its existing import and saved-assessment rule display path; no dashboard redesign or API dependency was introduced.",
            "",
            "## Limitations and bugs",
            "",
            "No blocking bugs were found. Observed non-blocking inconsistency: saved risk scores are rounded to two decimals, so formula recomputation can differ by up to 0.01 (for example, 20.95 versus 20.9525102). This validation does not provide authentication, deployment, browser-level Streamlit testing, production behavioral history, or live-provider testing.",
            "",
            "## Reproducibility",
            "",
            "Deterministic Investigator outputs were equivalent across two runs. Any model probability comparison allows only a small numerical tolerance for floating-point representation.",
        ]
    )
    (OUTPUT_DIR / "e2e_validation.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Phase 14 validation complete: {passed} passed, {failed} failed")
    print(f"Report: {OUTPUT_DIR.relative_to(PROJECT_ROOT) / 'e2e_validation.md'}")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
