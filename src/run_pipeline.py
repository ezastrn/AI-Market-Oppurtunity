"""Notebook-compatible end-to-end OSM market-screening pipeline."""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
import pandas as pd
import requests
import osmnx as ox

from src.config import load_config
from src.data_cleaning import clean_businesses
from src.data_collection import retrieve_boundary, retrieve_districts, retrieve_tag_sets, write_retrieval_metadata
from src.opportunity_scoring import evaluate_sufficiency, rank_candidates, score_cells
from src.report_generation import generate_report
from src.robustness_checks import compare_scenarios, stability_label
from src.spatial_analysis import (add_accessibility_indicator, add_competition_indicators,
                                  add_context_indicator, apply_eligibility_filter, create_grid)
from src.visualization import create_charts, create_opportunity_map


ROOT = Path(__file__).resolve().parents[1]


class DataAccessError(RuntimeError):
    """Raised when no approved OSM endpoint is currently usable."""


def run(config_path: str | Path) -> dict[str, Any]:
    """Run a real-data analysis, or fail clearly without fabricating outputs."""
    config = load_config(config_path)
    paths = {name: ROOT / "data" / name for name in ("raw", "processed", "outputs")}
    for path in paths.values(): path.mkdir(parents=True, exist_ok=True)
    try:
        config["retrieval"]["active_endpoint"] = _select_endpoint(config)
    except DataAccessError as error:
        summary = {"status": "INSUFFICIENT DATA", "failed_gates": ["data_access"], "message": str(error)}
        _write_summary(paths["outputs"], summary)
        generate_report(paths["outputs"], ROOT / "reports" / "market_intelligence_report.md", summary)
        return summary
    boundary = retrieve_boundary(config, paths["raw"])
    boundary_projected = boundary.to_crs(config["crs"]["projected"])
    _verify_boundary(boundary_projected)
    districts = retrieve_districts(paths["raw"])
    categories = _retrieve_categories(boundary, config, paths["raw"])
    selected, cleaned, feasibility = _select_category(categories, boundary, districts, config)
    _write_feasibility(feasibility, selected)
    if selected is None:
        summary = {"status": "INSUFFICIENT DATA", "failed_gates": ["category_selection"], "message": "No configured category passed the PRD feasibility rule."}
        _write_summary(paths["outputs"], summary); generate_report(paths["outputs"], ROOT / "reports" / "market_intelligence_report.md", summary)
        return summary
    cleaned.to_csv(paths["outputs"] / "cleaned_businesses.csv", index=False)
    cleaned.to_file(paths["processed"] / "cleaned_businesses.geojson", driver="GeoJSON")
    layers = _retrieve_support_layers(boundary, config, selected, paths["raw"])
    projected = {"buildings": layers["buildings"].to_crs(config["crs"]["projected"]), "landuse": layers["landuse"].to_crs(config["crs"]["projected"]), "roads": layers["roads"].to_crs(config["crs"]["projected"]), "context": {name: layer.to_crs(config["crs"]["projected"]) for name, layer in layers["context"].items()}}
    cells = create_grid(boundary_projected, config["grid"]["cell_size_m"], config["grid"]["min_inside_fraction"])
    cells = apply_eligibility_filter(cells, projected["buildings"], projected["landuse"], projected["roads"], config)
    competitors = cleaned.to_crs(config["crs"]["projected"])
    percentiles = tuple(config["scoring"]["winsor_percentiles"])
    cells = add_competition_indicators(cells, competitors, config["competitor"]["radius_m"], config["competitor"]["nearest_k"], percentiles, config["scoring"]["competition_weights"])
    cells, context_columns = add_context_indicator(cells, projected["context"], config["context"]["radius_m"], percentiles)
    cells = add_accessibility_indicator(cells, projected["roads"], percentiles)
    cells, excluded = score_cells(cells, config["scoring"]["weights"])
    district_count = int(cleaned.get("district", pd.Series(dtype=str)).dropna().nunique())
    summary = evaluate_sufficiency(cells, len(cleaned), district_count, config, 3 - len(excluded))
    summary.update({"category": selected, "data_quality": feasibility[selected]["quality"], "context_columns": context_columns, "excluded_components": excluded})
    if summary["status"] == "OK":
        baseline = rank_candidates(cells.assign(data_sufficiency_label="LOW"), config["ranking"]["top_n"])
        metrics, frequency = _run_required_scenarios(cells, competitors, config, baseline)
        cells = cells.merge(frequency, on="cell_id", how="left").fillna({"top_n_frequency": 0})
        cells["data_sufficiency_label"] = _sufficiency_labels(cells, competitors, boundary_projected, context_columns, config)
        candidates = rank_candidates(cells, config["ranking"]["top_n"])
        metrics.to_csv(paths["outputs"] / "robustness_metrics.csv", index=False)
        summary["robustness_label"] = stability_label(metrics)
    else:
        candidates = pd.DataFrame(columns=["cell_id", "rank", "score"])
    _export_outputs(cells, candidates, competitors, paths["outputs"])
    if summary["status"] == "OK":
        create_opportunity_map(cells, competitors, candidates, paths["outputs"] / "opportunity_map.html")
        create_charts(cells, paths["outputs"] / "charts")
    _write_summary(paths["outputs"], summary)
    write_retrieval_metadata(paths["raw"], config, [path.name for path in paths["raw"].glob("*.geojson")], True)
    generate_report(paths["outputs"], ROOT / "reports" / "market_intelligence_report.md", summary)
    return summary


def _select_endpoint(config: dict[str, Any]) -> str:
    """Probe primary/fallback Overpass endpoints with a minimal legal query."""
    endpoints = [config["retrieval"]["endpoint"], *config["retrieval"].get("fallback_endpoints", [])]
    failures = []
    query = "[out:json][timeout:25];node(around:1,-7.98,112.63)[amenity=cafe];out 1;"
    for endpoint in dict.fromkeys(endpoints):
        try:
            response = requests.post(endpoint, data={"data": query}, timeout=45, headers={"User-Agent": config["retrieval"]["user_agent"]})
            if response.ok:
                ox.settings.overpass_url = endpoint.removesuffix("/interpreter")
                return endpoint
            failures.append(f"{endpoint} returned HTTP {response.status_code}")
        except requests.RequestException as error:
            failures.append(f"{endpoint} unavailable ({type(error).__name__})")
    raise DataAccessError("No configured Overpass endpoint is available. " + "; ".join(failures) + ". Retry later or use a documented cached snapshot.")


def _verify_boundary(boundary: gpd.GeoDataFrame) -> None:
    if boundary.empty or not boundary.geometry.is_valid.all(): raise RuntimeError("Boundary is empty or invalid.")
    area_km2 = boundary.geometry.union_all().area / 1_000_000
    if not 99 <= area_km2 <= 121: raise RuntimeError(f"Boundary area {area_km2:.1f} km² is outside the PRD Kota Malang sanity range.")


def _retrieve_categories(boundary: gpd.GeoDataFrame, config: dict[str, Any], raw: Path) -> dict[str, gpd.GeoDataFrame]:
    return {name: retrieve_tag_sets(boundary, details["tags"], f"category_{name}", raw) for name, details in config["category"]["candidates"].items()}


def _select_category(categories: dict[str, gpd.GeoDataFrame], boundary: gpd.GeoDataFrame, districts: gpd.GeoDataFrame, config: dict[str, Any]) -> tuple[str | None, gpd.GeoDataFrame, dict[str, Any]]:
    evidence, options = {}, []
    for name, raw in categories.items():
        clean, quality = clean_businesses(raw, boundary, name, config["crs"]["projected"], config["deduplication"]["distance_m"])
        assignments = gpd.sjoin(clean, districts[["district", "geometry"]], how="left", predicate="within")
        clean["district"] = assignments["district"].reindex(clean.index)
        district_count = int(clean["district"].dropna().nunique())
        evidence[name] = {"records": len(clean), "districts": district_count, "quality": quality}
        if len(clean) >= config["sufficiency"]["min_competitors"] and district_count >= config["sufficiency"]["min_districts"]:
            options.append((name, clean))
    if not options: return None, gpd.GeoDataFrame(), evidence
    options.sort(key=lambda item: (len(item[1]), item[0]), reverse=True)
    return options[0][0], options[0][1], evidence


def _retrieve_support_layers(boundary: gpd.GeoDataFrame, config: dict[str, Any], category: str, raw: Path) -> dict[str, Any]:
    context = {name: retrieve_tag_sets(boundary, [tags], f"context_{category}_{name}", raw) for name, tags in config["category"]["candidates"][category]["context_features"].items()}
    return {"context": context, "buildings": retrieve_tag_sets(boundary, [{"building": True}], "buildings", raw), "landuse": retrieve_tag_sets(boundary, [{"landuse": True}], "landuse", raw), "roads": retrieve_tag_sets(boundary, [{"highway": config["accessibility"]["highway_classes"]}], "major_roads", raw)}


def _run_required_scenarios(cells: gpd.GeoDataFrame, competitors: gpd.GeoDataFrame, config: dict[str, Any], baseline: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    scenarios: dict[str, pd.DataFrame] = {}
    for name, weights in config["scoring"]["weight_scenarios"].items():
        scored, _ = score_cells(cells, weights)
        scenarios[f"weights_{name}"] = rank_candidates(scored.assign(data_sufficiency_label="LOW"), config["ranking"]["top_n"])
    percentiles = tuple(config["scoring"]["winsor_percentiles"])
    for radius in config["competitor"]["sensitivity_radii_m"]:
        recalculated = add_competition_indicators(cells, competitors, radius, config["competitor"]["nearest_k"], percentiles, config["scoring"]["competition_weights"])
        scored, _ = score_cells(recalculated, config["scoring"]["weights"])
        scenarios[f"radius_{radius}m"] = rank_candidates(scored.assign(data_sufficiency_label="LOW"), config["ranking"]["top_n"])
    metrics, frequency = compare_scenarios(baseline, scenarios, config["ranking"]["top_n"])
    return metrics, frequency


def _sufficiency_labels(cells: gpd.GeoDataFrame, competitors: gpd.GeoDataFrame, boundary: gpd.GeoDataFrame, context_columns: list[str], config: dict[str, Any]) -> pd.Series:
    boundary_edge = boundary.geometry.union_all().boundary
    labels = []
    for _, cell in cells.iterrows():
        centroid = cell.geometry.centroid
        factors = 0
        factors += centroid.distance(boundary_edge) >= config["competitor"]["radius_m"]
        factors += sum(cell.get(column, 0) > 0 for column in context_columns) >= 2
        nearby = competitors.loc[competitors.geometry.distance(centroid) <= config["context"]["radius_m"]]
        complete = (nearby["name"].notna().mean() >= config["sufficiency"]["local_complete_fraction"]) if len(nearby) else False
        factors += complete
        factors += cell.get("top_n_frequency", 0) >= .7
        labels.append("HIGH" if factors == 4 else "MEDIUM" if factors >= 2 else "LOW")
    return pd.Series(labels, index=cells.index)


def _export_outputs(cells: gpd.GeoDataFrame, candidates: pd.DataFrame, competitors: gpd.GeoDataFrame, output: Path) -> None:
    cells.to_crs("EPSG:4326").to_file(output / "cells.geojson", driver="GeoJSON")
    cells.drop(columns="geometry").to_csv(output / "cell_scores.csv", index=False)
    candidates.drop(columns="geometry", errors="ignore").to_csv(output / "candidate_ranking.csv", index=False)
    if not candidates.empty:
        gpd.GeoDataFrame(candidates, geometry="geometry", crs=cells.crs).to_crs("EPSG:4326").to_file(output / "candidates.geojson", driver="GeoJSON")


def _write_summary(output: Path, summary: dict[str, Any]) -> None:
    (output / "run_summary.json").write_text(json.dumps(summary, indent=2, default=str), encoding="utf-8")


def _write_feasibility(evidence: dict[str, Any], selected: str | None) -> None:
    target = ROOT / "docs" / "data_feasibility.md"
    target.write_text("# Data feasibility\n\nGenerated from real OSM retrieval.\n\n```json\n" + json.dumps(evidence, indent=2, default=str) + "\n```\n\nSelected category: `" + str(selected) + "`.\n", encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default="config/default_config.yaml")
    print(json.dumps(run(parser.parse_args().config), indent=2, default=str))
