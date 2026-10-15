"""Sensitivity metrics required for honest ranking interpretation."""
from __future__ import annotations

from collections.abc import Callable

import pandas as pd
from scipy.stats import spearmanr


def jaccard_overlap(first: set[str], second: set[str]) -> float:
    """Return top-N set overlap, treating two empty sets as identical."""
    union = first | second
    return len(first & second) / len(union) if union else 1.0


def compare_scenarios(baseline: pd.DataFrame, scenarios: dict[str, pd.DataFrame], top_n: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Compare scenarios to baseline and calculate per-cell top-N frequency."""
    baseline_top = set(baseline.nsmallest(top_n, "rank")["cell_id"])
    baseline_scores = baseline.set_index("cell_id")["score"]
    metrics, appearances = [], []
    for name, scenario in scenarios.items():
        scenario_top = set(scenario.nsmallest(top_n, "rank")["cell_id"])
        shared = baseline_scores.index.intersection(scenario.set_index("cell_id").index)
        correlation = spearmanr(baseline_scores.loc[shared], scenario.set_index("cell_id").loc[shared, "score"]).statistic if len(shared) >= 2 else float("nan")
        metrics.append({"scenario": name, "top_n_jaccard": jaccard_overlap(baseline_top, scenario_top), "spearman_score_correlation": correlation})
        appearances.extend({"scenario": name, "cell_id": cell_id, "in_top_n": cell_id in scenario_top} for cell_id in scenario["cell_id"])
    frequency = pd.DataFrame(appearances).groupby("cell_id", as_index=False)["in_top_n"].mean().rename(columns={"in_top_n": "top_n_frequency"}) if appearances else pd.DataFrame(columns=["cell_id", "top_n_frequency"])
    return pd.DataFrame(metrics), frequency


def stability_label(metrics: pd.DataFrame) -> str:
    """Classify median Jaccard according to the PRD initial thresholds."""
    median = metrics["top_n_jaccard"].median()
    if median >= .5:
        return "reasonably stable"
    if median >= .3:
        return "moderately sensitive"
    return "highly sensitive"
