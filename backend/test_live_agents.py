import asyncio
from datetime import datetime, timezone
import os

# Force live mode for testing
os.environ["DATA_MODE"] = "LIVE"

from app.schemas import Location
from app.agents import cyclone_agent, pfz_agent, ocean_agent
from app.data import live_client, advisory_scraper
import logging

logging.basicConfig(level=logging.INFO)

loc = Location(name="Test Port", latitude=18.9, longitude=72.8) # Mumbai
now = datetime.now(timezone.utc)

print("\n--- Testing Open-Meteo Currents ---")
try:
    marine_data = live_client.fetch_marine(loc.latitude, loc.longitude, now)
    print(f"Marine data keys: {list(marine_data.keys()) if marine_data else 'None'}")
    print(f"Current Speed: {marine_data.get('current_speed_ms')} m/s")
    print(f"Current Dir: {marine_data.get('current_direction_deg')} deg")
except Exception as e:
    print(f"Error: {e}")

print("\n--- Testing Ocean Agent (LIVE) ---")
try:
    res = ocean_agent.run(loc, now)
    print(f"Mode: {res.mode}")
    print(f"Source: {res.source}")
    print(f"Data: {res.data}")
except Exception as e:
    print(f"Error: {e}")

print("\n--- Testing Cyclone Agent (LIVE) ---")
try:
    res = cyclone_agent.run(loc, now)
    print(f"Mode: {res.mode}")
    print(f"Source: {res.source}")
    print(f"Alerts count: {res.data.get('count')}")
    print(f"Top alert: {res.data.get('alerts')[0] if res.data.get('alerts') else 'None'}")
except Exception as e:
    print(f"Error: {e}")

print("\n--- Testing PFZ Agent (LIVE) ---")
try:
    res = pfz_agent.run(loc, now)
    print(f"Mode: {res.mode}")
    print(f"Source: {res.source}")
    print(f"Zones count: {len(res.data.get('zones', []))}")
    if res.data.get('zones'):
        print(f"Top zone: {res.data.get('zones')[0]}")
except Exception as e:
    print(f"Error: {e}")

print("\n--- Done ---")
