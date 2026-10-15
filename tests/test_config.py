from copy import deepcopy
from pathlib import Path

import pytest

from src.config import ConfigError, load_config, validate_config


CONFIG_PATH = Path("config/default_config.yaml")


def test_default_config_is_valid():
    assert load_config(CONFIG_PATH)["crs"]["projected"] == "EPSG:32749"


def test_invalid_weight_sum_raises():
    config = load_config(CONFIG_PATH)
    config["scoring"]["weights"]["competition_gap"] = 0.9
    with pytest.raises(ConfigError, match="sum to 1"):
        validate_config(config)


def test_non_positive_radius_raises():
    config = load_config(CONFIG_PATH)
    config["competitor"]["radius_m"] = 0
    with pytest.raises(ConfigError, match="must be positive"):
        validate_config(config)


def test_unknown_selected_category_raises():
    config = load_config(CONFIG_PATH)
    config["category"]["name"] = "unknown"
    with pytest.raises(ConfigError, match="configured candidate"):
        validate_config(config)
