"""Normalization, scoring, sufficiency gates, and deterministic ranking."""
from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd


COMPONENT_COLUMNS = {
    "competition_gap": "competition_gap",
    "contextual_suitability": "contextual_suitability",
    "accessibility": "accessibility",
}


def normalize(values: pd.Series, higher_is_better: bool, percentiles: tuple[float, float] = (5, 95)) -> pd.Series:
    """Winsorize and scale values to [0, 1], returning NaN for no variation."""
    numeric = pd.to_numeric(values, errors="coerce")
    valid = numeric.dropna()
    if valid.empty or valid.nunique() <= 1:
        return pd.Series(np.nan, index=values.index, dtype=float)
    low, high = np.percentile(valid, percentiles)
    if np.isclose(low, high):
        return pd.Series(np.nan, index=values.index, dtype=float)
    scaled = (numeric.clip(low, high) - low) / (high - low)
    return scaled if higher_is_better else 1 - scaled


def combine_competition_gap(cells: pd.DataFrame, weights: dict[str, float], percentiles: tuple[float, float]) -> pd.Series:
    """Combine sparse-competition signals with higher values always favourable."""
    nearest = normalize(cells["nearest_competitor_m"], True, percentiles)
    count = normalize(cells["competitor_count"], False, percentiles)
    available = {"nearest_competitor_m": nearest, "competitor_count": count}
    usable = {name: weight for name, weight in weights.items() if name in available and available[name].notna().any()}
    if not usable:
        return pd.Series(np.nan, index=cells.index, dtype=float)
    total = sum(usable.values())
    return sum(available[name] * (weight / total) for name, weight in usable.items())


def score_cells(cells: pd.DataFrame, weights: dict[str, float]) -> tuple[pd.DataFrame, list[str]]:
    """Score cells, renormalizing only whole-run unavailable components.

    A cell with any missing usable component remains unrankable; it cannot gain
    from missing evidence.
    """
    result = cells.copy()
    available = [name for name, column in COMPONENT_COLUMNS.items() if column in result and result[column].notna().any()]
    excluded = [name for name in COMPONENT_COLUMNS if name not in available]
    if "competition_gap" not in available or len(available) < 2:
        result["run_status"] = "INSUFFICIENT DATA"
        result["score"] = np.nan
        return result, excluded
    active_weights = {name: weights[name] for name in available}
    weight_sum = sum(active_weights.values())
    active_weights = {name: value / weight_sum for name, value in active_weights.items()}
    result["run_status"] = "reduced_model" if excluded else "OK"
    for name, weight in active_weights.items():
        result[f"weight_{name}"] = weight
        result[f"contribution_{name}"] = result[COMPONENT_COLUMNS[name]] * weight
    contributions = [f"contribution_{name}" for name in active_weights]
    result["score"] = result[contributions].sum(axis=1, min_count=len(contributions)) * 100
    return result, excluded


def evaluate_sufficiency(cells: pd.DataFrame, competitor_count: int, district_count: int, config: dict[str, Any], components_available: int) -> dict[str, Any]:
    """Apply the PRD gates. A failed gate prevents ranking."""
    thresholds = config["sufficiency"]
    eligible_count = int(cells.get("eligible", pd.Series(dtype=bool)).sum())
    gates = {
        "G1_competitors": competitor_count >= thresholds["min_competitors"],
        "G2_eligible_cells": eligible_count >= thresholds["min_eligible_cells"],
        "G3_components": components_available >= 2,
        "G4_districts": district_count >= thresholds["min_districts"],
    }
    return {"status": "OK" if all(gates.values()) else "INSUFFICIENT DATA", "gates": gates,
            "failed_gates": [key for key, passed in gates.items() if not passed], "eligible_cells": eligible_count}


def rank_candidates(cells: pd.DataFrame, top_n: int) -> pd.DataFrame:
    """Rank eligible scored cells with PRD deterministic tie-breaking."""
    required = {"eligible", "score", "competition_gap", "cell_id"}
    missing = required - set(cells.columns)
    if missing:
        raise ValueError(f"Cannot rank without columns: {sorted(missing)}")
    candidates = cells.loc[cells["eligible"] & cells["score"].notna()].copy()
    sufficiency_order = {"HIGH": 3, "MEDIUM": 2, "LOW": 1}
    candidates["_sufficiency_order"] = candidates.get("data_sufficiency_label", "LOW").map(sufficiency_order).fillna(0)
    candidates = candidates.sort_values(["score", "competition_gap", "_sufficiency_order", "cell_id"], ascending=[False, False, False, True], kind="stable")
    candidates["rank"] = range(1, len(candidates) + 1)
    return candidates.head(top_n).drop(columns="_sufficiency_order")
