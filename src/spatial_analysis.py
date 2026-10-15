"""Projected-CRS grids, indicators, and eligibility filtering."""
from __future__ import annotations

import math
from typing import Any

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.geometry import Polygon

from src.opportunity_scoring import combine_competition_gap, normalize


def create_grid(boundary: gpd.GeoDataFrame, cell_size_m: float, min_inside_fraction: float) -> gpd.GeoDataFrame:
    """Create stable square cells that meet the configured in-boundary fraction."""
    if boundary.crs is None or not boundary.crs.is_projected:
        raise ValueError("Boundary must use a projected CRS before building a grid.")
    geometry = boundary.geometry.union_all()
    minx, miny, maxx, maxy = geometry.bounds
    start_x, start_y = math.floor(minx / cell_size_m) * cell_size_m, math.floor(miny / cell_size_m) * cell_size_m
    rows = []
    row = 0
    y = start_y
    while y < maxy:
        column, x = 0, start_x
        while x < maxx:
            cell = Polygon([(x, y), (x + cell_size_m, y), (x + cell_size_m, y + cell_size_m), (x, y + cell_size_m)])
            fraction = cell.intersection(geometry).area / cell.area
            if fraction >= min_inside_fraction:
                rows.append({"cell_id": f"r{row:04d}_c{column:04d}", "inside_fraction": fraction, "geometry": cell})
            x += cell_size_m
            column += 1
        y += cell_size_m
        row += 1
    return gpd.GeoDataFrame(rows, crs=boundary.crs)


def add_competition_indicators(cells: gpd.GeoDataFrame, competitors: gpd.GeoDataFrame, radius_m: float, nearest_k: int, percentiles: tuple[float, float], competition_weights: dict[str, float]) -> gpd.GeoDataFrame:
    """Calculate count, density, nearest distance, and Competition Gap."""
    _assert_matching_projected_crs(cells, competitors)
    result = cells.copy()
    points = result.geometry.centroid
    distances = [[point.distance(feature) for feature in competitors.geometry] for point in points]
    result["competitor_count"] = [sum(value <= radius_m for value in row) for row in distances]
    result["competitor_density_per_km2"] = result["competitor_count"] / (math.pi * radius_m**2 / 1_000_000)
    result["nearest_competitor_m"] = [min(row) if row else np.nan for row in distances]
    result["mean_nearest_k_m"] = [float(np.mean(sorted(row)[:nearest_k])) if len(row) >= nearest_k else np.nan for row in distances]
    result["competition_gap"] = combine_competition_gap(result, competition_weights, percentiles)
    return result


def add_context_indicator(cells: gpd.GeoDataFrame, context_layers: dict[str, gpd.GeoDataFrame], radius_m: float, percentiles: tuple[float, float]) -> tuple[gpd.GeoDataFrame, list[str]]:
    """Combine non-empty configured context layers; empty types are excluded."""
    result = cells.copy()
    available: list[str] = []
    centroids = result.geometry.centroid
    for feature_name, layer in context_layers.items():
        _assert_matching_projected_crs(result, layer)
        column = f"context_{feature_name}_count"
        result[column] = [sum(point.distance(feature) <= radius_m for feature in layer.geometry) for point in centroids]
        if len(layer) > 0:
            available.append(column)
    normalized = [normalize(result[column], True, percentiles) for column in available]
    result["contextual_suitability"] = pd.concat(normalized, axis=1).mean(axis=1) if normalized else np.nan
    return result, available


def add_accessibility_indicator(cells: gpd.GeoDataFrame, roads: gpd.GeoDataFrame, percentiles: tuple[float, float]) -> gpd.GeoDataFrame:
    """Use distance to configured major roads as a physical-connectivity proxy."""
    _assert_matching_projected_crs(cells, roads)
    result = cells.copy()
    centroids = result.geometry.centroid
    result["nearest_major_road_m"] = [min((point.distance(road) for road in roads.geometry), default=np.nan) for point in centroids]
    result["accessibility"] = normalize(result["nearest_major_road_m"], False, percentiles)
    return result


def apply_eligibility_filter(cells: gpd.GeoDataFrame, buildings: gpd.GeoDataFrame, landuse: gpd.GeoDataFrame, roads: gpd.GeoDataFrame, config: dict[str, Any]) -> gpd.GeoDataFrame:
    """Mark, but do not discard, cells based on built-environment evidence."""
    for layer in (buildings, landuse, roads):
        _assert_matching_projected_crs(cells, layer)
    result = cells.copy()
    rules = config["eligibility"]
    result["building_count"] = [sum(cell.intersects(item) for item in buildings.geometry) for cell in result.geometry]
    suitable = landuse.loc[landuse.get("landuse", pd.Series(index=landuse.index, dtype=str)).isin(rules["suitable_landuses"])]
    excluded = landuse.loc[landuse.get("landuse", pd.Series(index=landuse.index, dtype=str)).isin(rules["excluded_landuses"])]
    result["suitable_landuse_fraction"] = [_intersection_fraction(cell, suitable) for cell in result.geometry]
    result["excluded_landuse_fraction"] = [_intersection_fraction(cell, excluded) for cell in result.geometry]
    result["road_length_m"] = [sum(cell.intersection(road).length for road in roads.geometry) for cell in result.geometry]
    building_cells = result.loc[result["building_count"] > 0, "road_length_m"]
    threshold = float(np.percentile(building_cells, rules["road_length_percentile"])) if not building_cells.empty else float("inf")
    built = (result["building_count"] >= rules["min_building_count"]) | (result["suitable_landuse_fraction"] >= rules["min_suitable_landuse_fraction"]) | (result["road_length_m"] >= threshold)
    result["eligible"] = (result["inside_fraction"] >= config["grid"]["min_inside_fraction"]) & built & (result["excluded_landuse_fraction"] < rules["max_excluded_landuse_fraction"])
    result["eligibility_road_threshold_m"] = threshold
    return result


def _intersection_fraction(cell: Polygon, layer: gpd.GeoDataFrame) -> float:
    return sum(cell.intersection(geometry).area for geometry in layer.geometry) / cell.area if len(layer) else 0.0


def _assert_matching_projected_crs(first: gpd.GeoDataFrame, second: gpd.GeoDataFrame) -> None:
    if first.crs is None or second.crs is None or first.crs != second.crs or not first.crs.is_projected:
        raise ValueError("All spatial layers must share a projected CRS.")
