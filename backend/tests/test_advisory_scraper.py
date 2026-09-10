import pytest
from unittest.mock import MagicMock, patch

from app.data.advisory_scraper import (
    clear_scraper_cache,
    extract_text_from_html,
    scrape_imd_bulletin,
    scrape_incois_pfz,
)
from app.data.voyage_store import clear_voyages, get_voyage, start_voyage
from app.schemas_v2 import AdvisoryConstraint, DecisionState

SAMPLE_IMD_HTML = """<!DOCTYPE html>
<html>
<head><title>IMD Coastal Weather Warning</title></head>
<body>
  <h1>India Meteorological Department - Fishermen Warning</h1>
  <div class="warning-box">
    Squally weather with wind speed reaching 55 to 65 kmph gusting to 75 kmph is very likely along and off Maharashtra-Goa coasts.
    Fishermen are advised not to venture into these sea areas during next 24 hours.
  </div>
</body>
</html>
"""

SAMPLE_INCOIS_PFZ_HTML = """
<html>
<body>
  <h2>INCOIS Potential Fishing Zone Advisory</h2>
  <p>Oceanographic satellite analysis indicates potential fishing grounds:</p>
  <ul>
    <li>Location: 18.82 N, 72.68 E, Depth 40m, Distance 18.5 km offshore</li>
    <li>SST: 28.6 C, Chlorophyll: 1.55 mg/m3</li>
  </ul>
</body>
</html>
"""


@pytest.fixture(autouse=True)
def clean_all():
    clear_scraper_cache()
    clear_voyages()
    yield
    clear_scraper_cache()
    clear_voyages()


def test_extract_text_from_html():
    raw_html = "<html><head><script>var x=1;</script></head><body><h1>Warning</h1><p>Rough seas</p></body></html>"
    text = extract_text_from_html(raw_html)
    assert "Warning" in text
    assert "Rough seas" in text
    assert "var x" not in text


def test_scrape_imd_bulletin_and_sha256_cache():
    # 1. Scrape with HTML
    with patch("app.data.advisory_scraper.compile_advisory") as mock_compile:
        mock_adv = AdvisoryConstraint(
            authority="IMD",
            constraint_type="NO_GO",
            named_region="Maharashtra-Goa coasts",
            severity="SEVERE",
            valid_from=pytest.importorskip("datetime").datetime.now(pytest.importorskip("datetime").timezone.utc),
            valid_until=pytest.importorskip("datetime").datetime.now(pytest.importorskip("datetime").timezone.utc),
            source_text="Squally weather 55-65 kmph",
            source_reference="TEST-IMD-HTML",
            confidence=0.95,
        )
        mock_compile.return_value = [mock_adv]

        advisories = scrape_imd_bulletin(html_content=SAMPLE_IMD_HTML)
        assert len(advisories) == 1
        assert advisories[0].constraint_type == "NO_GO"
        assert mock_compile.call_count == 1

        # 2. Second scrape of exact same content -> SHA256 cache hit, compile_advisory not called again!
        advisories_cached = scrape_imd_bulletin(html_content=SAMPLE_IMD_HTML)
        assert len(advisories_cached) == 1
        assert mock_compile.call_count == 1


def test_scrape_incois_pfz_coordinates_and_params():
    zones = scrape_incois_pfz(html_content=SAMPLE_INCOIS_PFZ_HTML)
    assert len(zones) >= 1
    zone = zones[0]
    assert abs(zone["latitude"] - 18.82) < 0.01
    assert abs(zone["longitude"] - 72.68) < 0.01
    assert zone["distance_km"] == 18.5
    assert zone["sst_c"] == 28.6
    assert zone["chlorophyll_mg_m3"] == 1.55
    assert zone["source"] == "INCOIS"
