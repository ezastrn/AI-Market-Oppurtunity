"""Generate an honest report from output tables, never recalled numbers."""
from __future__ import annotations

from pathlib import Path

import pandas as pd


def generate_report(outputs_dir: str | Path, report_path: str | Path, run_summary: dict) -> Path:
    """Render a markdown report using pipeline output files only."""
    outputs, destination = Path(outputs_dir), Path(report_path)
    candidates_path = outputs / "candidate_ranking.csv"
    candidates = pd.read_csv(candidates_path) if candidates_path.exists() else pd.DataFrame()
    status = run_summary["status"]
    lines = ["# Market Intelligence Report", "", "## Executive summary", "",
             "**Interpretation:** A high score means low *observed* OSM competitor coverage plus supporting context in an eligible built-up cell. It does not mean demand, revenue, profit, commercial viability, or business success.", "",
             f"**Observation:** Run status: `{status}`.", ""]
    if status != "OK":
        lines += ["## Insufficient data", "", f"Ranking was intentionally withheld. Failed gates: {', '.join(run_summary.get('failed_gates', [])) or 'model availability' }.", "", "Suggested next step: inspect OSM coverage, choose a category with sufficient records, or adjust a documented grid-size setting."]
    else:
        lines += ["## Ranked candidate areas", "", "**Interpretation:** These cells merit validation, not investment decisions.", "", candidates.head(10).to_markdown(index=False), "", "## Suggested validation", "", "**Hypothesis:** High-ranking cells may warrant on-site foot-traffic observation, competitor verification, rental-price review, zoning checks, and customer research."]
    lines += ["", "## Data, assumptions, and limitations", "", "Data: © OpenStreetMap contributors, available under ODbL. OSM is community-maintained and incomplete coverage or inconsistent tagging can affect results. Absence of a mapped feature is not evidence of absence in reality.", "", "See `docs/methodology.md`, `docs/decision_log.md`, and raw retrieval metadata for reproducibility."]
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return destination
