"""Run the deterministic Phase 4 investigator against Phase 3 assessments.

Run all representative examples:
    .venv\\Scripts\\python scripts\\run_investigator.py

Investigate one source row:
    .venv\\Scripts\\python scripts\\run_investigator.py --source-row-id 215984
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from ai_investigator import ApplicationInvestigator
from investigator import report_to_markdown


PROJECT_ROOT = Path(__file__).resolve().parents[1]
ASSESSMENT_PATH = PROJECT_ROOT / "reports" / "behavioral" / "behavioral_risk_assessments.csv"
OUTPUT_DIR = PROJECT_ROOT / "reports" / "investigator"


def select_examples(assessments: pd.DataFrame) -> pd.DataFrame:
    """Select one deterministic, highest-scoring example from each available level."""
    examples = []
    for level in ("LOW", "MEDIUM", "HIGH"):
        candidates = assessments.loc[assessments["risk_level"] == level]
        if not candidates.empty:
            examples.append(
                candidates.sort_values(
                    ["risk_score", "ml_fraud_probability", "source_row_id"], ascending=[False, False, True]
                ).iloc[0]
            )
    return pd.DataFrame(examples)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate evidence-only RiskGuard AI investigation reports.")
    parser.add_argument("--source-row-id", type=int, help="Investigate one Phase 3 source row instead of representative examples.")
    arguments = parser.parse_args()

    if not ASSESSMENT_PATH.exists():
        raise FileNotFoundError(f"Assessment file not found: {ASSESSMENT_PATH}. Run scripts/run_behavioral_demo.py first.")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    assessments = pd.read_csv(ASSESSMENT_PATH)

    if arguments.source_row_id is None:
        selected = select_examples(assessments)
        output_stem = "sample_investigations"
    else:
        selected = assessments.loc[assessments["source_row_id"] == arguments.source_row_id]
        if selected.empty:
            raise ValueError(f"Source row {arguments.source_row_id} is not in the Phase 3 assessment output.")
        output_stem = f"investigation_{arguments.source_row_id}"

    investigator = ApplicationInvestigator()
    reports = [investigator.investigate(record) for record in selected.to_dict(orient="records")]
    (OUTPUT_DIR / f"{output_stem}.json").write_text(json.dumps(reports, indent=2), encoding="utf-8")
    markdown = "# RiskGuard AI — Phase 4 Investigation Reports\n\n" + "\n---\n\n".join(report_to_markdown(report) for report in reports)
    (OUTPUT_DIR / f"{output_stem}.md").write_text(markdown, encoding="utf-8")

    methodology = """# RiskGuard AI — Phase 4 Investigator Methodology

The application Investigator first constructs the existing deterministic report from a fixed whitelist of fields already present in the Phase 3 assessment. If `AI_PROVIDER_API_KEY` is configured, the guarded optional provider may add a validated advisory explanation. Without a key, or after any provider failure or invalid output, the deterministic report is returned.

The deterministic path uses no generative text, no extra transaction data, and no inferred facts. Its rule evidence is copied from the existing rule-engine explanation fields. Deterministic recommendations are fixed by the supplied risk level: LOW has no immediate escalation, MEDIUM recommends review, and HIGH recommends prioritised manual investigation. Every report states that it does not prove fraud.

The deterministic risk level, score, ML probability, behavioral points, and stored rule evidence remain authoritative. The provider cannot execute actions or change those values; recommendations are advisory only. Provider input is minimized and excludes raw model features, labels, and synthetic identifiers.

Synthetic `user_id`, `device_id`, `region`, `transaction_velocity`, `historical_average_amount`, and `amount_deviation` are always labelled as demo metadata, not real Kaggle customer information. The raw CSV is never read or modified by this phase.
"""
    (OUTPUT_DIR / "methodology.md").write_text(methodology, encoding="utf-8")
    print(f"Generated {len(reports)} deterministic investigation report(s) in {OUTPUT_DIR.relative_to(PROJECT_ROOT)}")


if __name__ == "__main__":
    main()
