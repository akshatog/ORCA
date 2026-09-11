import pytest
from unittest.mock import MagicMock, patch

from app.data.stormglass_client import (
    clear_cache,
    fetch_stormglass_point,
)


@pytest.fixture(autouse=True)
def clean():
    clear_cache()
    yield
    clear_cache()


def test_stormglass_fallback_without_key():
    with patch.dict("os.environ", {"STORMGLASS_API_KEY": ""}):
        res = fetch_stormglass_point(18.92, 72.83)
        assert res["mode"] == "DEMO"
        assert res["wave_height_m"] is not None
        assert res["current_speed_ms"] is not None
        assert "StormGlass" in res["source"]


def test_stormglass_live_parsing_and_caching():
    sample_response = {
        "hours": [
            {
                "waveHeight": {"sg": 1.75, "noaa": 1.6},
                "currentSpeed": {"sg": 0.85},
                "currentDirection": {"sg": 215.0},
                "waterTemperature": {"sg": 29.1},
            }
        ]
    }

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = sample_response

    mock_client = MagicMock()
    mock_client.get.return_value = mock_resp

    with patch.dict("os.environ", {"STORMGLASS_API_KEY": "fake-sg-key"}):
        # First call fetches live data
        res = fetch_stormglass_point(18.92, 72.83, client=mock_client)
        assert res["mode"] == "LIVE"
        assert res["wave_height_m"] == 1.75
        assert res["current_speed_ms"] == 0.85
        assert res["current_direction_deg"] == 215.0
        assert mock_client.get.call_count == 1

        # Second call to same ~0.1 deg coordinates hits cache
        cached = fetch_stormglass_point(18.94, 72.81, client=mock_client)
        assert cached["mode"] == "CACHED"
        assert cached["wave_height_m"] == 1.75
        assert mock_client.get.call_count == 1  # No additional network call!


def test_stormglass_error_fallback_no_crash():
    mock_resp = MagicMock()
    mock_resp.status_code = 402
    mock_resp.text = "Quota exceeded"

    mock_client = MagicMock()
    mock_client.get.return_value = mock_resp

    with patch.dict("os.environ", {"STORMGLASS_API_KEY": "fake-sg-key"}):
        res = fetch_stormglass_point(15.49, 73.82, client=mock_client)
        assert res["mode"] == "DEMO"
        assert res["wave_height_m"] is not None
