"""Deterministic synthetic demo context and transparent behavioral rules.

All fields created here are synthetic demonstration metadata. They are not
Kaggle source fields and are never used as inputs to the Phase 2 ML models.
"""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


SYNTHETIC_COLUMNS = [
    "user_id", "device_id", "region", "transaction_velocity",
    "historical_average_amount", "amount_deviation",
]
REGIONS = np.array(["North", "South", "East", "West", "Central"])
RULE_POINTS = {
    "high_transaction_velocity": 20,
    "unusual_device": 20,
    "unusual_region": 15,
    "high_transaction_amount": 20,
    "high_amount_deviation": 20,
}
AMOUNT_DEVIATION_THRESHOLD = 3.0
HISTORY_SEED_OFFSET = 1001


def add_synthetic_context(transactions: pd.DataFrame, seed: int) -> pd.DataFrame:
    """Attach reproducible, explicitly synthetic user/device/region context."""
    rng = np.random.default_rng(seed)
    enriched = transactions.copy()
    user_numbers = rng.integers(1, 501, size=len(enriched))
    home_device_numbers = (user_numbers - 1) % 200 + 1
    home_region_numbers = (user_numbers - 1) % len(REGIONS)

    # Most events use the synthetic user's usual device/region; the remainder
    # are deliberately unusual so the transparent rules have demo cases.
    unusual_device = rng.random(len(enriched)) < 0.12
    alternate_devices = rng.integers(1, 201, size=len(enriched))
    alternate_devices = np.where(alternate_devices == home_device_numbers, alternate_devices % 200 + 1, alternate_devices)
    device_numbers = np.where(unusual_device, alternate_devices, home_device_numbers)

    unusual_region = rng.random(len(enriched)) < 0.10
    alternate_regions = rng.integers(0, len(REGIONS), size=len(enriched))
    alternate_regions = np.where(alternate_regions == home_region_numbers, (alternate_regions + 1) % len(REGIONS), alternate_regions)
    region_numbers = np.where(unusual_region, alternate_regions, home_region_numbers)

    enriched["user_id"] = [f"demo_user_{number:03d}" for number in user_numbers]
    enriched["device_id"] = [f"demo_device_{number:03d}" for number in device_numbers]
    enriched["region"] = REGIONS[region_numbers]
    # Synthetic count of prior transactions in a recent window; it has no
    # relationship to a real customer's transaction history.
    enriched["transaction_velocity"] = rng.poisson(lam=1.8, size=len(enriched))

    # A separate seeded user-level baseline creates synthetic demonstration
    # history. It is independent of Amount, Class, model output, and scores.
    history_rng = np.random.default_rng(seed + HISTORY_SEED_OFFSET)
    user_historical_averages = history_rng.lognormal(mean=3.8, sigma=0.9, size=500)
    enriched["historical_average_amount"] = user_historical_averages[user_numbers - 1]
    enriched["amount_deviation"] = np.divide(
        enriched["Amount"].to_numpy(dtype=float),
        enriched["historical_average_amount"].to_numpy(dtype=float),
        out=np.zeros(len(enriched), dtype=float),
        where=enriched["historical_average_amount"].to_numpy(dtype=float) > 1e-9,
    )
    return enriched


def apply_behavioral_rules(enriched: pd.DataFrame, amount_threshold: float, velocity_threshold: int = 6) -> pd.DataFrame:
    """Apply simple, auditable rules and attach triggers plus explanations."""
    assessed = enriched.copy()
    user_numbers = assessed["user_id"].str.extract(r"(\d+)")[0].astype(int).to_numpy()
    expected_devices = np.array([f"demo_device_{((number - 1) % 200) + 1:03d}" for number in user_numbers])
    expected_regions = REGIONS[(user_numbers - 1) % len(REGIONS)]

    assessed["high_transaction_velocity_triggered"] = assessed["transaction_velocity"] >= velocity_threshold
    assessed["unusual_device_triggered"] = assessed["device_id"].to_numpy() != expected_devices
    assessed["unusual_region_triggered"] = assessed["region"].to_numpy() != expected_regions
    assessed["high_transaction_amount_triggered"] = assessed["Amount"] >= amount_threshold
    assessed["high_amount_deviation_triggered"] = assessed["amount_deviation"] >= AMOUNT_DEVIATION_THRESHOLD

    assessed["high_transaction_velocity_explanation"] = np.where(
        assessed["high_transaction_velocity_triggered"],
        f"Synthetic velocity is at least {velocity_threshold} transactions in the demo window.",
        "Synthetic velocity is below the demo threshold.",
    )
    assessed["unusual_device_explanation"] = np.where(
        assessed["unusual_device_triggered"],
        "Synthetic device differs from this demo user's usual device.",
        "Synthetic device matches this demo user's usual device.",
    )
    assessed["unusual_region_explanation"] = np.where(
        assessed["unusual_region_triggered"],
        "Synthetic region differs from this demo user's usual region.",
        "Synthetic region matches this demo user's usual region.",
    )
    assessed["high_transaction_amount_explanation"] = np.where(
        assessed["high_transaction_amount_triggered"],
        f"Real Kaggle Amount is at or above the subset 99th-percentile threshold ({amount_threshold:.2f}).",
        f"Real Kaggle Amount is below the subset 99th-percentile threshold ({amount_threshold:.2f}).",
    )
    assessed["high_amount_deviation_explanation"] = np.where(
        assessed["high_amount_deviation_triggered"],
        f"Synthetic amount is at least {AMOUNT_DEVIATION_THRESHOLD:.1f} times the synthetic historical average.",
        f"Synthetic amount is below {AMOUNT_DEVIATION_THRESHOLD:.1f} times the synthetic historical average.",
    )
    return assessed


def add_risk_assessment(assessed: pd.DataFrame, ml_fraud_probability: pd.Series | None = None) -> pd.DataFrame:
    """Create a documented score from independent ML and rule components.

    Score = min(100, 60 * ML probability + points for triggered rules).
    When no saved ML artifact is available, the ML component is explicitly zero;
    no probability is fabricated.
    """
    result = assessed.copy()
    if ml_fraud_probability is None:
        result["ml_fraud_probability"] = np.nan
        result["ml_signal_available"] = False
        ml_component = pd.Series(0.0, index=result.index)
    else:
        result["ml_fraud_probability"] = ml_fraud_probability
        result["ml_signal_available"] = True
        ml_component = 60 * result["ml_fraud_probability"].clip(0, 1)

    rule_columns = {rule: f"{rule}_triggered" for rule in RULE_POINTS}
    rule_score = sum(result[column].astype(int) * points for rule, points in RULE_POINTS.items() for column in [rule_columns[rule]])
    result["behavioral_rule_points"] = rule_score
    result["ml_risk_points"] = ml_component
    result["risk_score"] = (ml_component + rule_score).clip(upper=100).round(2)
    result["risk_level"] = pd.cut(
        result["risk_score"], bins=[-np.inf, 24.999, 49.999, np.inf], labels=["LOW", "MEDIUM", "HIGH"]
    ).astype(str)

    triggered_rule_names = []
    for _, row in result.iterrows():
        names = [rule.replace("_", " ").title() for rule, column in rule_columns.items() if row[column]]
        triggered_rule_names.append("; ".join(names) if names else "None")
    result["triggered_rules"] = triggered_rule_names
    result["risk_explanation"] = result.apply(
        lambda row: (
            f"Risk score {row['risk_score']:.2f}: {row['behavioral_rule_points']:.0f} behavioral-rule points "
            f"and {row['ml_risk_points']:.2f} ML points. Triggered rules: {row['triggered_rules']}."
        ),
        axis=1,
    )
    return result


def rule_counts(assessed: pd.DataFrame) -> dict[str, int]:
    """Return trigger counts keyed by stable rule names."""
    return {rule: int(assessed[f"{rule}_triggered"].sum()) for rule in RULE_POINTS}


def methodology(amount_threshold: float, velocity_threshold: int) -> dict[str, Any]:
    """Structured values used in the report and metadata output."""
    return {
        "synthetic_fields": SYNTHETIC_COLUMNS,
        "velocity_threshold": velocity_threshold,
        "amount_threshold": amount_threshold,
        "amount_deviation_threshold": AMOUNT_DEVIATION_THRESHOLD,
        "historical_average_generation": (
            "Seeded lognormal user-level synthetic baseline; independent of Amount, Class, model predictions, and risk scores"
        ),
        "history_seed_offset": HISTORY_SEED_OFFSET,
        "rule_points": RULE_POINTS,
        "risk_formula": "min(100, 60 * ml_fraud_probability + behavioral rule points)",
        "risk_levels": {"LOW": "score < 25", "MEDIUM": "25 <= score < 50", "HIGH": "score >= 50"},
    }
