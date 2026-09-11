import pytest

from app.data.source_registry import (
    clear_registry,
    get_primary_source,
    get_sources,
    init_default_sources,
    list_all_sources,
    register_source,
)


@pytest.fixture(autouse=True)
def reset_sources():
    clear_registry()
    init_default_sources()
    yield
    clear_registry()
    init_default_sources()


def test_get_sources_weather_ordered():
    sources = get_sources("weather")
    assert len(sources) >= 2
    assert sources[0].source_name == "Open-Meteo"
    assert sources[0].priority == 1
    assert sources[1].source_name == "StormGlass"
    assert sources[1].priority == 2


def test_get_primary_source():
    primary = get_primary_source("cyclone")
    assert primary is not None
    assert primary.source_name == "GDACS"


def test_custom_source_priority_sorting():
    # Register priority 0 source (should become new primary)
    register_source(
        capability="weather",
        source_name="HighRes radar",
        fetch_fn=lambda: None,
        priority=0,
        is_live=True,
    )
    primary = get_primary_source("weather")
    assert primary is not None
    assert primary.source_name == "HighRes radar"
    assert primary.priority == 0


def test_list_all_sources():
    all_s = list_all_sources()
    assert "weather" in all_s
    assert "ocean" in all_s
    assert "cyclone" in all_s
    assert "pfz" in all_s
