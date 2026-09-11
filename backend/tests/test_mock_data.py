from app.data.mock_data import (
    ALL_CASES,
    ALL_CASES_LIST,
    WEATHER_FIXTURES,
    ADVISORY_FIXTURES,
    PFZ_FIXTURES,
    CYCLONE_FIXTURES,
)
from app.schemas import Evidence, AdvisoryConstraint


def test_mock_data_all_cases_count_and_types():
    assert len(ALL_CASES) >= 7
    assert len(ALL_CASES_LIST) >= 7
    for name, ev in ALL_CASES.items():
        assert isinstance(ev, Evidence), f"{name} must be an instance of Evidence"
        assert 0.0 <= ev.confidence <= 1.0


def test_mock_data_standard_fixtures():
    assert len(WEATHER_FIXTURES) >= 3
    for ev in WEATHER_FIXTURES:
        assert isinstance(ev, Evidence)
        assert ev.source == "Open-Meteo" or ev.source == "INCOIS"

    assert len(ADVISORY_FIXTURES) >= 2
    for adv in ADVISORY_FIXTURES:
        assert isinstance(adv, AdvisoryConstraint)
        assert adv.confidence >= 0.70

    assert len(PFZ_FIXTURES) >= 1
    for pfz in PFZ_FIXTURES:
        assert isinstance(pfz, Evidence)
        assert isinstance(pfz.value, dict)

    assert len(CYCLONE_FIXTURES) >= 1
    for cyc in CYCLONE_FIXTURES:
        assert isinstance(cyc, Evidence)
        assert cyc.metric == "cyclone_alert"
