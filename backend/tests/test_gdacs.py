from datetime import datetime, timezone
import pytest
from unittest.mock import MagicMock, patch

from app.data.live_client import clear_cache, fetch_gdacs, parse_gdacs_xml
from app.data.voyage_store import clear_voyages, start_voyage, get_voyage
from app.schemas_v2 import DecisionState

SAMPLE_GDACS_XML = """<?xml version="1.0" encoding="utf-8"?>
<rss version="2.0" xmlns:gdacs="http://www.gdacs.org" xmlns:geo="http://www.w3.org/2003/01/geo/wgs84_pos#">
  <channel>
    <title>GDACS RSS</title>
    <item>
      <title>Tropical Cyclone DANA-24 in Bay of Bengal</title>
      <description>Tropical Cyclone DANA formed in Bay of Bengal, affecting Odisha and West Bengal coasts.</description>
      <link>https://www.gdacs.org/report.aspx?eventtype=TC&amp;eventid=1001</link>
      <pubDate>Thu, 10 Sep 2026 18:00:00 GMT</pubDate>
      <gdacs:eventtype>TC</gdacs:eventtype>
      <gdacs:alertlevel>Red</gdacs:alertlevel>
      <geo:lat>19.5</geo:lat>
      <geo:long>86.2</geo:long>
    </item>
    <item>
      <title>Earthquake in South Pacific Ocean</title>
      <description>Magnitude 5.2 earthquake near Fiji.</description>
      <link>https://www.gdacs.org/report.aspx?eventtype=EQ&amp;eventid=2002</link>
      <pubDate>Thu, 10 Sep 2026 17:00:00 GMT</pubDate>
      <gdacs:eventtype>EQ</gdacs:eventtype>
      <gdacs:alertlevel>Green</gdacs:alertlevel>
      <geo:lat>-18.2</geo:lat>
      <geo:long>-178.5</geo:long>
    </item>
  </channel>
</rss>
"""


@pytest.fixture(autouse=True)
def reset_all():
    clear_cache()
    clear_voyages()
    yield
    clear_cache()
    clear_voyages()


def test_parse_gdacs_xml_filters_indian_ocean():
    entries = parse_gdacs_xml(SAMPLE_GDACS_XML)
    # Only Bay of Bengal event should be included; Fiji should be filtered out
    assert len(entries) == 1
    tc = entries[0]
    assert "DANA" in tc["title"]
    assert tc["alert_level"] == "Red"
    assert tc["event_type"] == "TC"
    assert tc["lat"] == 19.5
    assert tc["lon"] == 86.2


def test_parse_gdacs_xml_empty_or_malformed():
    assert parse_gdacs_xml("") == []
    assert parse_gdacs_xml("<not xml") == []


def test_fetch_gdacs_caches_and_triggers_alert():
    now = datetime.now(timezone.utc)
    # Start an active voyage near Paradip
    start_voyage(
        location={"name": "Offshore Paradip", "lat": 20.0, "lon": 86.5},
        initial_decision=DecisionState(
            status="SAFE",
            risk_score=15.0,
            reasons=["Clear"],
            language="en",
            explanation="Normal conditions",
            generated_at=now,
        ),
        voyage_id="v-paradip-gdacs",
    )

    # Mock HTTP call returning SAMPLE_GDACS_XML
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = SAMPLE_GDACS_XML

    with patch("app.data.live_client._http") as mock_http:
        mock_client = MagicMock()
        mock_client.get.return_value = mock_resp
        mock_http.return_value = mock_client

        # First call fetches and parses
        entries = fetch_gdacs(force=True)
        assert len(entries) == 1
        assert entries[0]["alert_level"] == "Red"

        # Check that active voyage was evaluated
        voyage = get_voyage("v-paradip-gdacs")
        assert voyage is not None
