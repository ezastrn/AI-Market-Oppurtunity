"""Configuration loading and validation."""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pyproj
import yaml


class ConfigError(ValueError):
    """Raised when an analysis configuration is invalid."""


def load_config(path: str | Path) -> dict[str, Any]:
    """Load YAML configuration and fail early when required values are invalid."""
    with Path(path).open("r", encoding="utf-8") as stream:
        config = yaml.safe_load(stream)
    if not isinstance(config, dict):
        raise ConfigError("Configuration must be a YAML mapping.")
    validate_config(config)
    return config


def validate_config(config: dict[str, Any]) -> None:
    """Validate values that would otherwise cause misleading spatial results."""
    try:
        weights = config["scoring"]["weights"]
        crs = pyproj.CRS.from_user_input(config["crs"]["projected"])
    except (KeyError, pyproj.exceptions.CRSError) as error:
        raise ConfigError(f"Missing or invalid required configuration: {error}") from error
    if not crs.is_projected:
        raise ConfigError("crs.projected must be a projected CRS; geographic CRS values are unsafe for local distances.")
    _validate_weights(weights, "scoring.weights")
    for name, scenario in config["scoring"].get("weight_scenarios", {}).items():
        _validate_weights(scenario, f"scoring.weight_scenarios.{name}")
    positive_paths = [
        ("study_area.boundary_buffer_m", config["study_area"]["boundary_buffer_m"]),
        ("grid.cell_size_m", config["grid"]["cell_size_m"]),
        ("competitor.radius_m", config["competitor"]["radius_m"]),
        ("context.radius_m", config["context"]["radius_m"]),
        ("ranking.top_n", config["ranking"]["top_n"]),
    ]
    for name, value in positive_paths:
        if not isinstance(value, (int, float)) or value <= 0:
            raise ConfigError(f"{name} must be positive.")
    fraction_paths = [
        ("grid.min_inside_fraction", config["grid"]["min_inside_fraction"]),
        ("eligibility.max_excluded_landuse_fraction", config["eligibility"]["max_excluded_landuse_fraction"]),
    ]
    for name, value in fraction_paths:
        if not 0 <= value <= 1:
            raise ConfigError(f"{name} must be between 0 and 1.")
    candidates = config.get("category", {}).get("candidates", {})
    if not candidates or any(not item.get("tags") for item in candidates.values()):
        raise ConfigError("Each candidate category must have at least one OSM tag mapping.")
    selected = config.get("category", {}).get("name")
    if selected is not None and selected not in candidates:
        raise ConfigError("category.name must be null or name a configured candidate category.")


def _validate_weights(weights: dict[str, float], path: str) -> None:
    if not weights:
        raise ConfigError(f"{path} must contain at least one weight.")
    if any(not isinstance(value, (int, float)) or value < 0 for value in weights.values()):
        raise ConfigError(f"{path} values must be non-negative numbers.")
    if abs(sum(weights.values()) - 1.0) > 1e-6:
        raise ConfigError(f"{path} must sum to 1.0 (within 1e-6).")
