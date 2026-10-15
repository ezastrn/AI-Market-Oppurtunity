import numpy as np
import pandas as pd

from src.opportunity_scoring import evaluate_sufficiency, normalize, rank_candidates, score_cells


def test_normalization_direction_and_range():
    values = pd.Series([1, 2, 3, 4, 5])
    assert normalize(values, True).between(0, 1).all()
    assert normalize(values, False).iloc[0] > normalize(values, False).iloc[-1]


def test_missing_component_does_not_raise_score():
    cells = pd.DataFrame({"competition_gap": [0.9, 0.2], "contextual_suitability": [0.1, np.nan], "accessibility": [0.5, 0.5]})
    scored, excluded = score_cells(cells, {"competition_gap": .34, "contextual_suitability": .33, "accessibility": .33})
    assert excluded == []
    assert np.isnan(scored.loc[1, "score"])


def test_ranking_is_deterministic_and_eligible_only():
    cells = pd.DataFrame({"cell_id": ["b", "a", "x"], "eligible": [True, True, False], "score": [80, 80, 99], "competition_gap": [.5, .5, 1], "data_sufficiency_label": ["LOW", "LOW", "HIGH"]})
    ranked = rank_candidates(cells, 10)
    assert ranked["cell_id"].tolist() == ["a", "b"]


def test_failed_gate_prevents_ranking():
    config = {"sufficiency": {"min_competitors": 30, "min_eligible_cells": 50, "min_districts": 4}}
    result = evaluate_sufficiency(pd.DataFrame({"eligible": [True] * 10}), 4, 1, config, 3)
    assert result["status"] == "INSUFFICIENT DATA"
