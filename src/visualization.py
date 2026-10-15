"""Interactive map and concise analytical charts."""
from __future__ import annotations

from pathlib import Path

import folium
import geopandas as gpd
import matplotlib.pyplot as plt
import pandas as pd


DISCLAIMER = "Screening result, not a verified profitable location. © OpenStreetMap contributors"


def create_opportunity_map(cells: gpd.GeoDataFrame, competitors: gpd.GeoDataFrame, candidates: pd.DataFrame, destination: str | Path) -> Path:
    """Create a map with boundary cells, competitors, attribution, and disclaimer."""
    display_cells, display_competitors = cells.to_crs("EPSG:4326"), competitors.to_crs("EPSG:4326")
    center = [display_cells.geometry.centroid.y.mean(), display_cells.geometry.centroid.x.mean()]
    result = folium.Map(location=center, zoom_start=12, control_scale=True, tiles="OpenStreetMap", attr="© OpenStreetMap contributors")
    candidate_ids = set(candidates.get("cell_id", []))
    for _, cell in display_cells.iterrows():
        eligible, score = cell.get("eligible", False), cell.get("score")
        color = "#d3d3d3" if not eligible else ("#238b45" if cell["cell_id"] in candidate_ids else "#74c476")
        tooltip = f"{cell['cell_id']} | score: {score:.1f}" if pd.notna(score) else f"{cell['cell_id']} | ineligible/unscored"
        folium.GeoJson(cell.geometry, style_function=lambda _, value=color: {"fillColor": value, "color": "#555", "weight": 1, "fillOpacity": .55}, tooltip=tooltip).add_to(result)
    for _, business in display_competitors.iterrows():
        folium.CircleMarker([business.geometry.y, business.geometry.x], radius=3, color="#c51b8a", fill=True, fill_opacity=.8, tooltip=str(business.get("name") or "Mapped competitor")).add_to(result)
    folium.map.Marker([center[0], center[1]], icon=folium.DivIcon(html=f"<div style='font-size:12px;background:white;padding:6px'>{DISCLAIMER}</div>")).add_to(result)
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    result.save(target)
    return target


def create_charts(cells: pd.DataFrame, destination_dir: str | Path) -> list[Path]:
    """Write score distribution and top-candidate contribution charts."""
    target = Path(destination_dir)
    target.mkdir(parents=True, exist_ok=True)
    outputs: list[Path] = []
    plt.figure(figsize=(8, 4))
    cells.loc[cells.get("eligible", False), "score"].dropna().plot.hist(bins=20, color="#238b45")
    plt.xlabel("Opportunity score (0–100)"); plt.ylabel("Eligible cells"); plt.title("Score distribution — screening only")
    score_path = target / "score_distribution.png"; plt.tight_layout(); plt.savefig(score_path, dpi=150); plt.close(); outputs.append(score_path)
    contribution_columns = [column for column in cells if column.startswith("contribution_")]
    if contribution_columns:
        top = cells.nlargest(10, "score").set_index("cell_id")[contribution_columns]
        top.plot.barh(stacked=True, figsize=(9, 5)); plt.xlabel("Weighted normalized contribution"); plt.title("Top-cell factor contributions")
        contribution_path = target / "candidate_contributions.png"; plt.tight_layout(); plt.savefig(contribution_path, dpi=150); plt.close(); outputs.append(contribution_path)
    return outputs
