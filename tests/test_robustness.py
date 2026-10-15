import pandas as pd

from src.robustness_checks import compare_scenarios, jaccard_overlap, stability_label


def test_jaccard_and_frequency():
    baseline = pd.DataFrame({"cell_id": ["a", "b", "c"], "rank": [1, 2, 3], "score": [90, 80, 70]})
    scenario = pd.DataFrame({"cell_id": ["a", "c", "b"], "rank": [1, 2, 3], "score": [89, 79, 69]})
    metrics, frequency = compare_scenarios(baseline, {"radius_300": scenario}, 2)
    assert metrics.loc[0, "top_n_jaccard"] == 1 / 3
    assert frequency["top_n_frequency"].between(0, 1).all()
    assert stability_label(metrics) == "moderately sensitive"


def test_empty_sets_are_identical():
    assert jaccard_overlap(set(), set()) == 1
