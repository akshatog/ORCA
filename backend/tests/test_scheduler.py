import pytest
from unittest.mock import patch

from app.data.scheduler import (
    get_scheduler_status,
    start_scheduler,
    stop_scheduler,
)


@pytest.fixture(autouse=True)
def tear_down():
    yield
    stop_scheduler()


def test_scheduler_registers_all_five_tiered_jobs():
    sched = start_scheduler(run_warmup=False)
    assert sched.running is True

    status = get_scheduler_status()
    assert status["status"] == "running"
    assert status["job_count"] == 5

    registered_ids = {j["id"] for j in status["jobs"]}
    expected_ids = {
        "fetch_gdacs_and_alert",
        "fetch_open_meteo_cache",
        "fetch_imd_advisory",
        "fetch_stormglass_cache",
        "fetch_incois_pfz",
    }
    assert registered_ids == expected_ids

    # Stop scheduler
    stop_scheduler()
    assert get_scheduler_status()["status"] == "stopped"


def test_scheduler_warmup_calls_all_fetchers():
    with patch("app.data.scheduler.job_fetch_gdacs") as mock_gdacs, \
         patch("app.data.scheduler.job_fetch_open_meteo") as mock_meteo, \
         patch("app.data.scheduler.job_fetch_imd_advisory") as mock_imd, \
         patch("app.data.scheduler.job_fetch_stormglass") as mock_sg, \
         patch("app.data.scheduler.job_fetch_incois_pfz") as mock_pfz:

        start_scheduler(run_warmup=True)

        assert mock_gdacs.call_count == 1
        assert mock_meteo.call_count == 1
        assert mock_imd.call_count == 1
        assert mock_sg.call_count == 1
        assert mock_pfz.call_count == 1
