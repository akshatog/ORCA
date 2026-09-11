import pytest
from app.services.route_optimizer import plan_routes, score_route_path
from app.schemas import RouteLeg, RouteOption, WaypointCondition
from app.config import ROUTE_SCORING


def test_score_route_path_waypoint_count_and_fields():
    # 2 coordinates approx 33.5 km apart
    legs = [
        RouteLeg(latitude=18.90, longitude=72.80),
        RouteLeg(latitude=18.80, longitude=72.50),
    ]
    route = RouteOption(
        name="Test route",
        kind="safest",
        legs=legs,
        distance_km=33.5,
        eta_minutes=140,
        risk_score=35,
        risk_category="MODERATE",
    )
    scored = score_route_path(route, origin_wave=1.5, origin_wind=25.0)

    assert len(scored.waypoint_conditions) == 5  # ROUTE_SCORING.samples_per_route
    assert scored.path_risk_score is not None
    assert 0.0 <= scored.path_risk_score <= 100.0

    for idx, wp in enumerate(scored.waypoint_conditions):
        assert isinstance(wp, WaypointCondition)
        assert 0.0 <= wp.risk_factor <= 1.0
        assert wp.risk_level in ("LOW", "MODERATE", "HIGH", "EXTREME")
        if idx == 0:
            assert wp.distance_from_start_km == 0.0
        if idx == 4:
            assert pytest.approx(wp.distance_from_start_km, abs=0.5) == 33.5


def test_storm_band_penalty_and_reranking():
    # Localized storm cell between lon 72.60 and 72.70 at lat 18.85
    def storm_cell_weather(lat, lon):
        if 18.80 <= lat <= 18.90 and 72.60 <= lon <= 72.70:
            return (4.2, 65.0)  # Severe storm band
        return (1.2, 18.0)      # Calm seas

    # Route A goes directly through the storm cell
    legs_a = [
        RouteLeg(latitude=18.85, longitude=72.75),
        RouteLeg(latitude=18.85, longitude=72.65),  # direct hit into storm center
        RouteLeg(latitude=18.85, longitude=72.55),
    ]
    route_storm = RouteOption(
        name="Storm track",
        kind="shortest",
        legs=legs_a,
        distance_km=21.0,
        eta_minutes=70,
        risk_score=40,
        risk_category="MODERATE",
    )

    # Route B detours around the storm cell to the north (lat 18.95)
    legs_b = [
        RouteLeg(latitude=18.85, longitude=72.75),
        RouteLeg(latitude=18.95, longitude=72.65),  # detours well north of storm
        RouteLeg(latitude=18.85, longitude=72.55),
    ]
    route_clear = RouteOption(
        name="Clear detour",
        kind="safest",
        legs=legs_b,
        distance_km=28.0,
        eta_minutes=95,
        risk_score=35,
        risk_category="MODERATE",
    )

    scored_storm = score_route_path(route_storm, weather_cell_fn=storm_cell_weather)
    scored_clear = score_route_path(route_clear, weather_cell_fn=storm_cell_weather)

    # The storm track must have a significantly higher path risk score due to the spike penalty
    assert scored_storm.path_risk_score > scored_clear.path_risk_score + 15.0

    # Storm track contains an EXTREME or HIGH risk waypoint
    storm_levels = [w.risk_level for w in scored_storm.waypoint_conditions]
    assert "EXTREME" in storm_levels or "HIGH" in storm_levels


def test_plan_routes_includes_waypoint_conditions():
    # Calling plan_routes directly
    options = plan_routes(
        origin=(18.92, 72.83),  # Sassoon Dock
        dest=(18.75, 72.65),    # PFZ area
        wave_m=1.3,
        wind_kmh=22.0,
    )
    assert len(options) >= 2
    for opt in options:
        assert len(opt.waypoint_conditions) >= 2
        assert opt.path_risk_score is not None
        assert 0.0 <= opt.path_risk_score <= 100.0
