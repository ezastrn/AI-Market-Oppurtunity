"""Cached OSM retrieval with explicit metadata and no synthetic fallbacks."""
from __future__ import annotations

import json
import platform
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import geopandas as gpd
import osmnx as ox
import pandas as pd


def retrieve_boundary(config: dict[str, Any], raw_dir: str | Path) -> gpd.GeoDataFrame:
    """Fetch and cache the configured administrative boundary."""
    raw_path = Path(raw_dir)
    ox.settings.overpass_url = config["retrieval"]["active_endpoint"].removesuffix("/interpreter")
    ox.settings.http_user_agent = config["retrieval"]["user_agent"]
    cache = raw_path / "boundary.geojson"
    if cache.exists():
        return gpd.read_file(cache)
    boundary = ox.geocode_to_gdf(config["study_area"]["boundary_query"])
    boundary.to_file(cache, driver="GeoJSON")
    return boundary


def retrieve_districts(raw_dir: str | Path) -> gpd.GeoDataFrame:
    """Retrieve and cache the five Kota Malang kecamatan boundaries."""
    raw_path = Path(raw_dir)
    cache = raw_path / "districts.geojson"
    if cache.exists():
        return gpd.read_file(cache)
    names = ["Klojen", "Blimbing", "Kedungkandang", "Sukun", "Lowokwaru"]
    layers = []
    for name in names:
        layer = ox.geocode_to_gdf(f"{name}, Kota Malang, East Java, Indonesia")
        layer["district"] = name
        layers.append(layer[["district", "geometry"]])
    districts = gpd.GeoDataFrame(pd.concat(layers, ignore_index=True), geometry="geometry", crs=layers[0].crs)
    districts.to_file(cache, driver="GeoJSON")
    return districts


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


def retrieve_tag_sets(boundary: gpd.GeoDataFrame, tag_sets: list[dict[str, Any]], label: str, raw_dir: str | Path) -> gpd.GeoDataFrame:
    """Retrieve the union of multiple OSM tag predicates into one cached layer."""
    raw_path = Path(raw_dir)
    cache = raw_path / f"{label}.geojson"
    if cache.exists():
        return gpd.read_file(cache)
    layers = []
    for tags in tag_sets:
        layer = ox.features_from_polygon(boundary.geometry.union_all(), tags).reset_index(names=["osm_type", "osm_id"])
        if not layer.empty:
            layers.append(layer)
    if not layers:
        return gpd.GeoDataFrame(columns=["feature_id", "geometry"], geometry="geometry", crs=boundary.crs)
    features = gpd.GeoDataFrame(pd.concat(layers, ignore_index=True), geometry="geometry", crs=layers[0].crs)
    features["feature_id"] = features["osm_type"].astype(str) + "/" + features["osm_id"].astype(str)
    features = features.drop_duplicates("feature_id")
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
