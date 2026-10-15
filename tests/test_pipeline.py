from unittest.mock import Mock, patch

import pytest

from src.run_pipeline import DataAccessError, _select_endpoint


def test_endpoint_selection_uses_first_healthy_endpoint():
    config = {"retrieval": {"endpoint": "https://primary/api/interpreter", "fallback_endpoints": ["https://backup/api/interpreter"], "user_agent": "test"}}
    failed, healthy = Mock(ok=False, status_code=502), Mock(ok=True, status_code=200)
    with patch("src.run_pipeline.requests.post", side_effect=[failed, healthy]):
        assert _select_endpoint(config) == "https://backup/api/interpreter"


def test_endpoint_selection_raises_clear_error_when_all_fail():
    config = {"retrieval": {"endpoint": "https://primary/api/interpreter", "fallback_endpoints": [], "user_agent": "test"}}
    with patch("src.run_pipeline.requests.post", return_value=Mock(ok=False, status_code=503)):
        with pytest.raises(DataAccessError, match="No configured Overpass endpoint"):
            _select_endpoint(config)
