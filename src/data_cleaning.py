"""Traceable validation, category normalization, and deduplication."""
from __future__ import annotations

import json
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

import geopandas as gpd
import pandas as pd
from shapely.geometry import Point


REQUIRED_COLUMNS = ("feature_id", "geometry")


def clean_businesses(
    records: gpd.GeoDataFrame,
    boundary: gpd.GeoDataFrame,
    category: str,
    projected_crs: str,
    duplicate_distance_m: float = 30,
) -> tuple[gpd.GeoDataFrame, dict[str, int]]:
    """Return valid in-boundary records and an auditable data-quality summary."""
    for column in REQUIRED_COLUMNS:
        if column not in records:
            raise ValueError(f"Business records require '{column}'.")
    if records.crs is None or boundary.crs is None:
        raise ValueError("Business records and boundary must have a CRS.")
    summary = {"retrieved": len(records), "invalid_removed": 0, "outside_boundary": 0,
               "duplicates_merged": 0, "retained": 0}
    result = records.copy()
    valid = result.geometry.notna() & ~result.geometry.is_empty & result.geometry.is_valid
    summary["invalid_removed"] = int((~valid).sum())
    result = result.loc[valid].copy()
    result["geometry_type"] = result.geometry.geom_type.str.lower().replace({"polygon": "polygon", "multipolygon": "polygon"})
    result["geometry"] = result.geometry.map(_representative_point)
    result = result.to_crs(projected_crs)
    boundary_projected = boundary.to_crs(projected_crs)
    within = result.geometry.map(lambda geometry: boundary_projected.geometry.union_all().covers(geometry))
    summary["outside_boundary"] = int((~within).sum())
    result = result.loc[within].copy()
    result = _standardize_columns(result, category)
    before_deduplication = len(result)
    result = _deduplicate(result, duplicate_distance_m)
    summary["duplicates_merged"] = before_deduplication - len(result)
    result = result.to_crs("EPSG:4326")
    result["longitude"] = result.geometry.x
    result["latitude"] = result.geometry.y
    summary["retained"] = len(result)
    return result, summary


def _representative_point(geometry: Any) -> Point:
    return geometry if geometry.geom_type == "Point" else geometry.representative_point()


def _standardize_columns(records: gpd.GeoDataFrame, category: str) -> gpd.GeoDataFrame:
    result = records.copy()
    result["name"] = result.get("name", pd.Series(index=result.index, dtype="object"))
    result["category"] = category
    result["source"] = result.get("source", "OpenStreetMap")
    result["retrieved_at"] = result.get("retrieved_at", datetime.now(timezone.utc).isoformat())
    tags = result.get("source_tags", pd.Series([{}] * len(result), index=result.index))
    result["source_tags"] = tags.map(lambda value: json.dumps(value) if isinstance(value, Mapping) else str(value))
    result["data_quality_flag"] = result.get("data_quality_flag", "")
    missing_name = result["name"].isna() | result["name"].astype(str).str.strip().eq("")
    result.loc[missing_name, "data_quality_flag"] = result.loc[missing_name, "data_quality_flag"].map(_append_missing_name)
    return result


def _append_missing_name(value: str) -> str:
    return "missing_name" if not value else f"{value};missing_name"


def _deduplicate(records: gpd.GeoDataFrame, threshold_m: float) -> gpd.GeoDataFrame:
    result = records.drop_duplicates(subset=["feature_id"], keep="first").copy()
    keep: list[int] = []
    for index, row in result.iterrows():
        name = row.get("name")
        if pd.isna(name) or not str(name).strip():
            keep.append(index)
            continue
        earlier = result.loc[keep]
        same_name = earlier["name"].fillna("").str.casefold().eq(str(name).casefold())
        same_category = earlier["category"].eq(row["category"])
        duplicate = False
        for _, candidate in earlier.loc[same_name & same_category].iterrows():
            if row.geometry.distance(candidate.geometry) <= threshold_m:
                duplicate = True
                break
        if not duplicate:
            keep.append(index)
    return result.loc[keep].copy()
