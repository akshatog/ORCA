import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch
from app.schemas import WaypointCondition
from app.graph.nodes import _pfz_potential_from_chlorophyll, _build_cyclone_alerts_for_risk_engine
from app.schemas_v2 import AdvisoryConstraint, make_evidence

FRONTEND_REQUIRED_FIELDS = {'lat','lon','distance_from_start_km','wave_m','wind_kmh','risk_factor','risk_level'}

def test_waypoint_condition_field_names_match_frontend():
    wp = WaypointCondition(lat=18.92, lon=72.83, distance_from_start_km=5.0, wave_m=1.5, wind_kmh=25.0, risk_factor=0.35, risk_level='MODERATE')
    missing = FRONTEND_REQUIRED_FIELDS - set(wp.model_dump())
    assert not missing, f'Backend missing FE fields: {missing}'

def test_waypoint_condition_no_phantom_fields():
    OLD = {'segment_risk','latitude','longitude','wave_height_m','wind_speed_kmh'}
    wp = WaypointCondition(lat=18.92, lon=72.83, distance_from_start_km=5.0, wave_m=1.5, wind_kmh=25.0, risk_factor=0.35, risk_level='MODERATE')
    assert not (OLD & set(wp.model_dump())), 'Phantom old field names detected'

def test_pfz_potential_from_chlorophyll_thresholds():
    assert _pfz_potential_from_chlorophyll(1.50) == 'HIGH'
    assert _pfz_potential_from_chlorophyll(1.20) == 'HIGH'
    assert _pfz_potential_from_chlorophyll(1.19) == 'MEDIUM'
    assert _pfz_potential_from_chlorophyll(0.60) == 'MEDIUM'
    assert _pfz_potential_from_chlorophyll(0.59) == 'LOW'
    assert _pfz_potential_from_chlorophyll(None) == 'MEDIUM'

def test_route_node_uses_real_pfz_coordinates():
    from app.graph.nodes import route_node
    pfz_ev = make_evidence(metric='pfz_zone',
        value={'rank':1,'latitude':18.50,'longitude':71.90,'distance_km':45.0,
               'chlorophyll_mg_m3':1.35,'confidence':0.92,'rationale':'test','source':'DEMO'},
        source='INCOIS', confidence=0.92, authority_level='official_forecast', mode='DEMO')
    state = MagicMock()
    state.location = {'name':'Mumbai','lat':18.92,'lon':72.83}
    state.evidence = [pfz_ev]
    state.decision = None
    state.advisories = []
    cap = {}
    def fake_run(loc, when, destination=None, destination_name=None, **kw):
        cap['lat'] = destination[0]; cap['lon'] = destination[1]; cap['name'] = destination_name
        r = MagicMock(); r.ok = True; r.data = {'options':[{'distance_km':52.0}]}; return r
    with patch('app.graph.nodes.route_agent.run', side_effect=fake_run):
        route_node(state)
    assert abs(cap['lat'] - 18.50) < 0.01, f'BE-001: expected lat 18.50, got {cap["lat"]}'
    assert abs(cap['lon'] - 71.90) < 0.01, f'BE-001: expected lon 71.90, got {cap["lon"]}'
    assert 'PFZ' in cap['name']

def test_route_node_fallback_when_no_pfz():
    from app.graph.nodes import route_node
    state = MagicMock()
    state.location = {'name':'Mumbai','lat':18.92,'lon':72.83}
    state.evidence = []; state.decision = None; state.advisories = []
    cap = {}
    def fake_run(loc, when, destination=None, destination_name=None, **kw):
        cap['lat'] = destination[0]; cap['name'] = destination_name
        r = MagicMock(); r.ok = True; r.data = {'options':[{'distance_km':20.0}]}; return r
    with patch('app.graph.nodes.route_agent.run', side_effect=fake_run):
        route_node(state)
    assert cap['lat'] is not None
    assert 'Open Water' in cap['name']

def test_build_cyclone_alerts_for_risk_engine():
    now = datetime.now(timezone.utc)
    advisories = [
        AdvisoryConstraint(authority='IMD', constraint_type='NO_GO', named_region='MH',
            severity='SEVERE', valid_from=now, valid_until=now,
            source_text='Cyclone warning', source_reference='IMD-001', confidence=0.95),
        AdvisoryConstraint(authority='INCOIS', constraint_type='CAUTION', named_region='KL',
            severity='MODERATE', valid_from=now, valid_until=now,
            source_text='Rough seas', source_reference='INCOIS-002', confidence=0.80),
    ]
    result = _build_cyclone_alerts_for_risk_engine(advisories)
    assert len(result) == 2
    assert result[0]['severity'] == 'severe'
    assert result[0]['official'] is True
    assert result[0]['headline'] == 'Cyclone warning'
    assert result[1]['type'] == 'fishermen_warning'

def test_constraint_engine_calls_risk_engine_assess():
    from app.graph.nodes import constraint_engine_node
    wave_ev = make_evidence(metric='wave_height', value=3.5, unit='m', source='DEMO',
                            confidence=0.9, authority_level='external_forecast', mode='DEMO')
    wind_ev = make_evidence(metric='wind_speed', value=45.0, unit='km/h', source='DEMO',
                            confidence=0.9, authority_level='external_forecast', mode='DEMO')
    state = MagicMock(); state.evidence = [wave_ev, wind_ev]; state.advisories = []; state.language = 'en'
    called = {}
    import app.graph.nodes as nm
    orig = nm.risk_engine.assess
    def spy(**kw): called.update(kw); return orig(**kw)
    with patch.object(nm.risk_engine, 'assess', side_effect=spy):
        result = constraint_engine_node(state)
    assert called, 'risk_engine.assess not called - DUP-001 regression'
    assert abs(called.get('wave_height_m', 0) - 3.5) < 0.01
    assert abs(called.get('wind_speed_kmh', 0) - 45.0) < 0.01
    dec = result['decision']
    assert dec.status in ('SAFE','CAUTION','UNSAFE','INSUFFICIENT_EVIDENCE')
    assert 0.0 <= dec.risk_score <= 100.0

def test_constraint_engine_deterministic_floors_preserved():
    from app.graph.nodes import constraint_engine_node
    from app.config import RISK
    extreme_wave = float(RISK.wave_danger_m) + 1.0
    wave_ev = make_evidence(metric='wave_height', value=extreme_wave, unit='m', source='DEMO',
                            confidence=0.9, authority_level='external_forecast', mode='DEMO')
    state = MagicMock(); state.evidence = [wave_ev]; state.advisories = []; state.language = 'en'
    result = constraint_engine_node(state)
    dec = result['decision']
    assert dec.risk_score >= float(RISK.wave_danger_floor)
    assert dec.status in ('UNSAFE', 'CAUTION')
