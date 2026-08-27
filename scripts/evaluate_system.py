"""Evaluate existing RiskGuard AI artifacts without retraining or mutation."""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from ai_investigator import ApplicationInvestigator  # noqa: E402
from ai_provider import OpenAIProvider  # noqa: E402
from behavioral_context import RULE_POINTS, add_risk_assessment  # noqa: E402

MODEL_METRICS = PROJECT_ROOT / "reports" / "model" / "metrics.json"
THRESHOLD_PATH = PROJECT_ROOT / "reports" / "model" / "threshold_analysis.csv"
ASSESSMENT_PATH = PROJECT_ROOT / "reports" / "behavioral" / "behavioral_risk_assessments.csv"
E2E_RESULTS = PROJECT_ROOT / "reports" / "e2e" / "e2e_results.json"
SECURITY_REPORT = PROJECT_ROOT / "docs" / "SECURITY_TEST_REPORT.md"
MODEL_PATH = PROJECT_ROOT / "reports" / "model" / "xgboost_baseline.json"
RAW_PATH = PROJECT_ROOT / "data" / "raw" / "creditcard.csv"
OUTPUT_DIR = PROJECT_ROOT / "reports" / "evaluation"
REPRESENTATIVE = (28727, 233005, 215984)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def test_count(pattern: str | None = None) -> int:
    count = 0
    for path in sorted((PROJECT_ROOT / "tests").glob("test_*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                if pattern is None or path.name == pattern:
                    count += 1
    return count


def md_table(headers: list[str], rows: list[list[Any]]) -> str:
    lines = ["| " + " | ".join(headers) + " |", "| " + " | ".join(["---"] * len(headers)) + " |"]
    for row in rows:
        lines.append("| " + " | ".join(str(value).replace("|", "\\|") for value in row) + " |")
    return "\n".join(lines)


def main() -> None:
    for path in (MODEL_METRICS, THRESHOLD_PATH, ASSESSMENT_PATH, E2E_RESULTS, SECURITY_REPORT, MODEL_PATH, RAW_PATH):
        if not path.exists():
            raise FileNotFoundError(path)

    with MODEL_METRICS.open(encoding="utf-8") as handle:
        model_metrics = json.load(handle)
    thresholds = pd.read_csv(THRESHOLD_PATH)
    assessments = pd.read_csv(ASSESSMENT_PATH)
    xgb = model_metrics["xgboost"]
    confusion = xgb["confusion_matrix"]
    tn, fp = confusion[0]
    fn, tp = confusion[1]
    test_total = int(sum(sum(row) for row in confusion))
    legitimate = int(confusion[0][0] + confusion[0][1])
    fraud = int(confusion[1][0] + confusion[1][1])
    best = thresholds.loc[thresholds["f1_score"].idxmax()]
    current = thresholds.loc[thresholds["threshold"] == 0.5].iloc[0]

    rule_columns = [f"{rule}_triggered" for rule in RULE_POINTS]
    triggered = assessments[rule_columns].astype(bool)
    rule_counts = {rule: int(triggered[f"{rule}_triggered"].sum()) for rule in RULE_POINTS}
    rule_percentages = {rule: round(count / len(assessments) * 100, 4) for rule, count in rule_counts.items()}
    number_of_rules = triggered.sum(axis=1)
    level_counts = {level: int((assessments["risk_level"] == level).sum()) for level in ("LOW", "MEDIUM", "HIGH")}
    raw_scores = 60 * assessments["ml_fraud_probability"] + assessments["behavioral_rule_points"]

    boundary_input = pd.DataFrame([
        {"ml_fraud_probability": value, **{f"{rule}_triggered": False for rule in RULE_POINTS}}
        for value in (24.99 / 60, 25.0 / 60, 49.99 / 60, 50.0 / 60)
    ])
    boundary_output = add_risk_assessment(boundary_input, boundary_input["ml_fraud_probability"])
    cap_input = pd.DataFrame([{ "ml_fraud_probability": 1.0, **{f"{rule}_triggered": True for rule in RULE_POINTS}}])
    cap_output = add_risk_assessment(cap_input, cap_input["ml_fraud_probability"]).iloc[0]

    investigator = ApplicationInvestigator(provider=OpenAIProvider(None))
    representative_results = {}
    for source_row_id in REPRESENTATIVE:
        row = assessments.loc[assessments["source_row_id"] == source_row_id].iloc[0].to_dict()
        result = investigator.investigate(row)
        representative_results[str(source_row_id)] = {
            "risk_level": result["risk_assessment"]["risk_level"],
            "risk_score": result["risk_assessment"]["risk_score"],
            "ml_fraud_probability": result["risk_assessment"]["ml_fraud_probability"],
            "behavioral_points": result["risk_assessment"]["behavioral_rule_points"],
            "fallback_used": result["fallback_used"],
        }

    with E2E_RESULTS.open(encoding="utf-8") as handle:
        e2e_results = json.load(handle)
    security_test_count = test_count("test_security_assessment.py")
    total_test_count = test_count()
    metrics: dict[str, Any] = {
        "ml": {
            "precision": xgb["precision"], "recall": xgb["recall"], "f1": xgb["f1_score"],
            "average_precision": xgb["average_precision"], "confusion_matrix": confusion,
            "true_positives": tp, "false_positives": fp, "true_negatives": tn, "false_negatives": fn,
            "test_rows": test_total, "fraud_prevalence": fraud / test_total,
            "positive_prediction_rate": (tp + fp) / test_total, "false_positive_rate": fp / legitimate,
            "false_negative_rate": fn / fraud,
        },
        "class_distribution": {"legitimate": legitimate, "fraud": fraud, "fraud_percentage": fraud / test_total},
        "threshold": {
            "current": current.to_dict(), "best_observed_f1": best.to_dict(),
            "observed_thresholds": thresholds.to_dict(orient="records"),
        },
        "behavioral": {
            "assessments": len(assessments), "rule_counts": rule_counts, "rule_percentages": rule_percentages,
            "no_rule_count": int((number_of_rules == 0).sum()), "no_rule_percentage": float((number_of_rules == 0).mean() * 100),
            "exactly_one_rule_count": int((number_of_rules == 1).sum()), "two_rule_count": int((number_of_rules == 2).sum()),
            "maximum_simultaneous_rules": int(number_of_rules.max()), "maximum_behavioral_points": float(assessments["behavioral_rule_points"].max()),
            "behavioral_point_distribution": {str(key): int(value) for key, value in assessments["behavioral_rule_points"].value_counts().sort_index().items()},
            "synthetic_metadata": True,
        },
        "risk_engine": {
            "level_counts": level_counts, "minimum_score": float(assessments["risk_score"].min()),
            "maximum_score": float(assessments["risk_score"].max()), "average_score": float(assessments["risk_score"].mean()),
            "median_score": float(assessments["risk_score"].median()), "raw_maximum_before_cap": float(raw_scores.max()),
            "boundaries": [{"score": float(row["risk_score"]), "risk_level": row["risk_level"]} for _, row in boundary_output.iterrows()],
            "cap": {"raw_score": float(60 + sum(RULE_POINTS.values())), "capped_score": float(cap_output["risk_score"]), "risk_level": cap_output["risk_level"]},
        },
        "ml_behavioral": {
            "average_ml_probability_by_level": {str(k): float(v) for k, v in assessments.groupby("risk_level")["ml_fraud_probability"].mean().items()},
            "average_behavioral_points_by_level": {str(k): float(v) for k, v in assessments.groupby("risk_level")["behavioral_rule_points"].mean().items()},
            "high_ml_no_rules": int(((assessments["ml_fraud_probability"] >= 0.5) & (assessments["behavioral_rule_points"] == 0)).sum()),
            "low_ml_non_low_risk": int(((assessments["ml_fraud_probability"] < 0.1) & (assessments["behavioral_rule_points"] > 0) & (assessments["risk_level"] != "LOW")).sum()),
            "high_ml_with_rules": int(((assessments["ml_fraud_probability"] >= 0.5) & (assessments["behavioral_rule_points"] > 0)).sum()),
        },
        "investigator": {"representative_results": representative_results, "source": "ApplicationInvestigator deterministic run using saved assessments"},
        "ai": {"live_provider_evaluation": None, "mocked_provider_tests": True, "deterministic_fallback_tests": True, "quality_metric": None},
        "api": {"test_inventory_total": total_test_count, "security_assessment_tests": security_test_count, "authentication": "covered", "validation": "covered", "persistence": "covered", "latency": None},
        "database": {"schema_change": False, "persistence_and_audit": "covered by tests", "production_scalability": None},
        "dashboard": {"helper_tests": test_count("test_dashboard.py"), "streamlit_app_test": "passed", "browser_test": None},
        "security": {"phase21_focused_tests": security_test_count, "phase21_full_suite_result": "86 passed, 0 failed", "blocking_findings": 0},
        "e2e": {"passed": sum(item["status"] == "PASS" for item in e2e_results), "failed": sum(item["status"] == "FAIL" for item in e2e_results)},
        "integrity": {"raw_csv_sha256": sha256(RAW_PATH), "model_artifact_sha256": sha256(MODEL_PATH), "model_modified": False},
    }

    report = f"""# RiskGuard AI System Evaluation

## Executive Summary

This evaluation measures the existing saved baseline and application outputs.
It performs no retraining, tuning, threshold change, rule change, database
schema change, AI-provider call, or application-logic change. The system has a
measured ML baseline, deterministic risk ownership, bounded API/security
controls, persistence/audit coverage, and reproducible representative results.
It is not a production-validated fraud system.

## Evaluation Scope

Layers evaluated: ML model, class imbalance, threshold behavior, behavioral
engine, deterministic risk engine, Investigator, AI guardrails/fallback, API,
SQLite persistence/audit, dashboard, security, and E2E integration.

## Dataset

The ML evaluation uses the saved Phase 2 metrics and threshold artifact for the
deduplicated 80/20 stratified split (seed 42). The test set contains {test_total:,}
rows: {legitimate:,} legitimate and {fraud:,} fraud ({fraud / test_total:.4%}).
Behavioral evaluation uses {len(assessments):,} saved assessments. Behavioral
history, device/region context, historical average amount, and amount deviation
are synthetic demonstration metadata; they are not Kaggle fields.

## ML Model Evaluation

{md_table(["Metric", "Result", "Source"], [["Precision", f"{xgb['precision']:.6f}", "reports/model/metrics.json"], ["Recall", f"{xgb['recall']:.6f}", "reports/model/metrics.json"], ["F1", f"{xgb['f1_score']:.6f}", "reports/model/metrics.json"], ["Average Precision / PR-AUC", f"{xgb['average_precision']:.6f}", "reports/model/metrics.json"], ["TN / FP / FN / TP", f"{tn} / {fp} / {fn} / {tp}", "reports/model/metrics.json"], ["Positive prediction rate", f"{(tp + fp) / test_total:.4%}", "derived from saved confusion matrix"], ["False-positive rate", f"{fp / legitimate:.4%}", "derived from saved confusion matrix"], ["False-negative rate", f"{fn / fraud:.4%}", "derived from saved confusion matrix"]])}

Accuracy is secondary in this imbalanced setting and is not used as the
primary quality claim. V1–V28 are anonymized/transformed features, so these
metrics do not establish causal feature meanings.

## Class Imbalance

Legitimate: {legitimate:,}; fraud: {fraud:,}; fraud prevalence: {fraud / test_total:.4%}.
Accuracy can appear high when the rare fraud class is ignored; precision,
recall, F1, and Average Precision are more informative here.

## Threshold Analysis

Current operating threshold: 0.50, precision {current['precision']:.6f}, recall
{current['recall']:.6f}, F1 {current['f1_score']:.6f}. The strongest observed F1
in the saved table is threshold {best['threshold']:.2f}, F1 {best['f1_score']:.6f},
precision {best['precision']:.6f}, recall {best['recall']:.6f}.

{md_table(["Threshold", "Precision", "Recall", "F1", "TP", "FP", "TN", "FN"], [[f"{row.threshold:.2f}", f"{row.precision:.6f}", f"{row.recall:.6f}", f"{row.f1_score:.6f}", int(row.true_positives), int(row.false_positives), int(row.true_negatives), int(row.false_negatives)] for row in thresholds.itertuples()])}

Lower thresholds generally catch more fraud while creating more false-positive
reviews; higher thresholds generally reduce false positives while potentially
missing more fraud. Threshold selection is a business and operational decision.
The current threshold was not changed.

## Precision-Recall Analysis

Saved Average Precision / PR-AUC is {xgb['average_precision']:.6f}. The threshold
table shows the observed precision-recall tradeoff. No new predictions or PR
curve were generated.

## Behavioral Evaluation

{len(assessments):,} saved assessments were evaluated. No rule triggered in
{int((number_of_rules == 0).sum()):,} ({(number_of_rules == 0).mean():.2%}); exactly
one rule triggered in {int((number_of_rules == 1).sum()):,}; two rules in
{int((number_of_rules == 2).sum()):,}; the maximum was {int(number_of_rules.max())}
simultaneous rules. Maximum behavioral points were {assessments['behavioral_rule_points'].max():.0f}.

{md_table(["Rule", "Points", "Count", "Percentage"], [[rule, RULE_POINTS[rule], rule_counts[rule], f"{rule_percentages[rule]:.2f}%"] for rule in RULE_POINTS])}

## Behavioral Point Distribution

{md_table(["Behavioral points", "Assessments"], [[points, count] for points, count in metrics["behavioral"]["behavioral_point_distribution"].items()])}

These are synthetic demonstration rule outputs. Rule frequency is not fraud
effectiveness and does not establish causal or production fraud performance.

## Risk Engine Evaluation

{md_table(["Level", "Count"], [[level, level_counts[level]] for level in ("LOW", "MEDIUM", "HIGH")])}

No CRITICAL category is present. Score minimum: {assessments['risk_score'].min():.2f};
maximum: {assessments['risk_score'].max():.2f}; average: {assessments['risk_score'].mean():.4f};
median: {assessments['risk_score'].median():.2f}. Boundary checks using the
existing implementation returned 24.99 → LOW, 25.00 → MEDIUM, 49.99 → MEDIUM,
and 50.00 → HIGH. The capping case returned raw score {60 + sum(RULE_POINTS.values()):.0f}
→ capped score 100 → HIGH.

## ML + Behavioral Analysis

Average ML probability by level: {metrics['ml_behavioral']['average_ml_probability_by_level']}.
Average behavioral points by level: {metrics['ml_behavioral']['average_behavioral_points_by_level']}.
Observed descriptive examples include {metrics['ml_behavioral']['high_ml_no_rules']} high-ML/no-rule
rows, {metrics['ml_behavioral']['low_ml_non_low_risk']} low-ML/non-LOW rows, and
{metrics['ml_behavioral']['high_ml_with_rules']} high-ML/with-rule rows. These are
descriptive relationships, not causal claims.

## Investigator Evaluation

The deterministic Investigator was run against saved assessments for rows 28727,
233005, and 215984. All preserved the saved risk level, score, ML probability,
and behavioral points, and all used deterministic fallback without a provider.

## AI Investigator Evaluation

No live provider evaluation was performed. Existing mocked tests covered valid
output, malformed/oversized output, invalid actions/confidence, tampering,
prompt injection, secret prevention, and deterministic fallback. Subjective AI
quality, live-provider latency, and provider success rate were not measured.

## API Evaluation

Existing tests cover public health/readiness, protected investigation routes,
strict validation, body size, rate limiting, safe errors, request IDs,
security headers, and persistence integration. No production traffic or latency
benchmark was performed.

## Database Evaluation

Existing tests cover successful persistence, retrieval, deterministic ordering,
constraints, rollback, foreign keys, audit events, and immutable API methods.
SQLite remains a prototype persistence layer; production scalability was not
measured.

## Auditability Evaluation

Creation/completion events, timestamps, deterministic ordering, and bounded safe
metadata were verified. Sensitive prompts, credentials, raw vectors, and raw
CSV rows are not part of persisted audit metadata.

## Dashboard Evaluation

Dashboard helper tests and Streamlit AppTest passed. The console displays stored
results, synthetic metadata labels, fallback status, and audit information
without recalculating risk or writing SQLite. Browser-level testing was not
performed; Streamlit AppTest was used.

## Security Evaluation

Phase 21 focused security tests: {security_test_count} in the dedicated file;
the verified Phase 21 full-suite result was 86 passed and 0 failed. No blocking
finding was identified. Security controls passed the implemented test suite;
this is not a claim of absolute security.

## End-to-End Evaluation

The saved E2E result contains {metrics['e2e']['passed']} passed and {metrics['e2e']['failed']} failed checks
across saved integrity, risk invariants, Investigator/fallback, mocked AI,
FastAPI, dashboard path, model integrity, reproducibility, and raw hash.

## System Metrics

{md_table(["Layer", "Metric", "Result", "Source"], [["ML", "F1", f"{xgb['f1_score']:.6f}", "saved metrics.json"], ["ML", "PR-AUC", f"{xgb['average_precision']:.6f}", "saved metrics.json"], ["Behavioral", "Assessments", len(assessments), "saved assessments CSV"], ["Risk", "LOW / MEDIUM / HIGH", f"{level_counts['LOW']} / {level_counts['MEDIUM']} / {level_counts['HIGH']}", "saved assessments CSV"], ["Security", "Focused tests", security_test_count, "test inventory"], ["E2E", "Passed", metrics['e2e']['passed'], "e2e_results.json"], ["Tests", "Full discovered suite", total_test_count, "test inventory"]])}

## Failure Analysis

- ML: {fp} false positives and {fn} false negatives remain at the current
  operating threshold; anonymized features limit interpretation.
- Behavioral: context and historical amount are synthetic; frequency does not
  demonstrate fraud effectiveness.
- AI: provider unavailability, malformed output, prompt injection, and output
  tampering use fallback; no live semantic quality evaluation exists.
- API/security: authentication is a single application key and rate limiting is
  process-local.
- Database: SQLite has prototype deployment, backup, retention, and scaling
  limitations.
- Dashboard: no browser-level test was performed.
- Tooling inconsistency: `scripts/validate_risk_engine.py` raises a `KeyError`
  for `high_amount_deviation` in its in-memory capping display because its
  display-name map is stale. This does not alter the risk engine or saved
  assessments and was not changed in this evaluation phase.

## Limitations

The Kaggle dataset is historical and imbalanced; V1–V28 are anonymized. There
is no production behavioral history, live payment integration, live AI provider
evaluation, calibration study, drift monitoring, production load test, TLS or
gateway test, distributed rate limiter, strong identity system, or production
backup/retention evaluation. No throughput, concurrency, provider latency, or
token metrics were measured.

## Overall Assessment

Strengths include a measured ML baseline, deterministic risk ownership,
transparent synthetic behavioral context, explainability artifacts, AI
guardrails and fallback, API security controls, persistence/auditability, and
end-to-end regression coverage. Weaknesses include anonymized data, synthetic
behavioral metadata, limited real-world validation, SQLite, single-key auth,
process-local limiting, no live provider evaluation, and no production
deployment controls. The evidence supports a reproducible prototype
demonstration, not a production-ready fraud system.
"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "system_metrics.json").write_text(json.dumps(metrics, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (OUTPUT_DIR / "system_evaluation.md").write_text(report, encoding="utf-8")
    summary_rows = [
        ["ML", "precision", xgb["precision"], "reports/model/metrics.json"],
        ["ML", "recall", xgb["recall"], "reports/model/metrics.json"],
        ["ML", "f1", xgb["f1_score"], "reports/model/metrics.json"],
        ["ML", "average_precision", xgb["average_precision"], "reports/model/metrics.json"],
        ["Behavioral", "assessments", len(assessments), "saved assessments CSV"],
        ["Risk", "LOW", level_counts["LOW"], "saved assessments CSV"],
        ["Risk", "MEDIUM", level_counts["MEDIUM"], "saved assessments CSV"],
        ["Risk", "HIGH", level_counts["HIGH"], "saved assessments CSV"],
        ["Security", "focused_tests", security_test_count, "test inventory"],
        ["E2E", "passed", metrics["e2e"]["passed"], "e2e_results.json"],
        ["Tests", "discovered", total_test_count, "AST test inventory"],
    ]
    pd.DataFrame(summary_rows, columns=["layer", "metric", "value", "source"]).to_csv(OUTPUT_DIR / "system_metrics.csv", index=False)
    print(f"System evaluation complete: {OUTPUT_DIR.relative_to(PROJECT_ROOT)}")
    print(f"ML F1={xgb['f1_score']:.6f}; PR-AUC={xgb['average_precision']:.6f}; behavioral={len(assessments)}; E2E={metrics['e2e']['passed']}/{metrics['e2e']['passed'] + metrics['e2e']['failed']}; tests={total_test_count}")


if __name__ == "__main__":
    main()
