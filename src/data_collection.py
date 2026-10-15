"""Cached OSM retrieval with explicit metadata and no synthetic fallbacks."""
from __future__ import annotations

import json
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
import osmnx as ox


def retrieve_boundary(config: dict[str, Any], raw_dir: str | Path) -> gpd.GeoDataFrame:
    """Fetch and cache the configured administrative boundary."""
    raw_path = Path(raw_dir)
    cache = raw_path / "boundary.geojson"
    if cache.exists():
        return gpd.read_file(cache)
    boundary = ox.geocode_to_gdf(config["study_area"]["boundary_query"])
    boundary.to_file(cache, driver="GeoJSON")
    return boundary


def retrieve_features(boundary: gpd.GeoDataFrame, tags: dict[str, Any], label: str, raw_dir: str | Path) -> gpd.GeoDataFrame:
    """Fetch a tagged OSM layer or load its immutable cached GeoJSON snapshot."""
    raw_path = Path(raw_dir)
    cache = raw_path / f"{label}.geojson"
    if cache.exists():
        return gpd.read_file(cache)
    features = ox.features_from_polygon(boundary.geometry.union_all(), tags)
    features = features.reset_index(names=["osm_type", "osm_id"])
    features["feature_id"] = features["osm_type"].astype(str) + "/" + features["osm_id"].astype(str)
    features.to_file(cache, driver="GeoJSON")
    return features


def write_retrieval_metadata(raw_dir: str | Path, config: dict[str, Any], files: list[str], endpoint_reachable: bool) -> Path:
    """Write the provenance required to reproduce a raw OSM snapshot."""
    target = Path(raw_dir) / "retrieval_metadata.json"
    payload = {"retrieved_at": datetime.now(timezone.utc).isoformat(), "source": "OpenStreetMap via OSMnx/Overpass",
               "endpoint": config["retrieval"]["endpoint"], "endpoint_reachable": endpoint_reachable,
               "files": files, "python": platform.python_version(), "osmnx": ox.__version__,
               "attribution": "© OpenStreetMap contributors, ODbL 1.0"}
    target.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return target
