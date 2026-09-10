"""Comprehensive smoke test for all ORCA 2.0 API endpoints.

Tests:
- GET /api/health
- POST /api/chat (legacy endpoint)
- POST /plan (LangGraph planner)
- GET /trace/{request_id} (trace retrieval)
- POST /voyages/start (active voyage initiation)
- GET /voyages/active (active voyages list)
- POST /alerts/trigger (real-time alert trigger & nearest safe port)
- POST /voyages/{id}/end (end voyage)
- POST /voice/transcribe (STT endpoint)
- POST /voice/speak (TTS endpoint)
"""
import base64
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def run_smoke_test() -> int:
    print("=" * 80)
    print("ORCA 2.0 — COMPREHENSIVE END-TO-END API SMOKE TEST")
    print("=" * 80)
    failures = []

    # 1. Health
    print("[1/10] Testing GET /api/health ...", end=" ")
    res = client.get("/api/health")
    if res.status_code == 200 and res.json().get("status") == "ok":
        print("PASS")
    else:
        print(f"FAIL ({res.status_code}: {res.text})")
        failures.append("GET /api/health failed")

    # 2. Legacy Chat
    print("[2/10] Testing POST /api/chat (legacy) ...", end=" ")
    res = client.post("/api/chat", json={"message": "Can I fish near Goa tomorrow morning?", "session_id": "smoke-chat-1"})
    if res.status_code == 200 and "answer" in res.json() and "trace" in res.json():
        data = res.json()
        print(f"PASS (Risk: {data.get('risk', {}).get('category')}, Routes: {len(data.get('routes', []))})")
    else:
        print(f"FAIL ({res.status_code}: {res.text})")
        failures.append("POST /api/chat failed")

    # 3. LangGraph Plan
    print("[3/10] Testing POST /plan (LangGraph pipeline) ...", end=" ")
    plan_payload = {
        "location": {"lat": 18.922, "lon": 72.8346, "name": "Mumbai"},
        "query": "Can I safely go fishing near Mumbai tomorrow morning?",
        "language": "en"
    }
    res = client.post("/plan", json=plan_payload)
    request_id = None
    if res.status_code == 200:
        data = res.json()
        request_id = data.get("request_id") or res.headers.get("X-Request-ID")
        status_val = data.get("status")
        risk_score = data.get("risk_score")
        route = data.get("route") or {}
        advisories = data.get("active_advisories", [])
        req_display = (request_id[:8] + "...") if request_id else "header-id"
        print(f"PASS (Status: {status_val}, Risk: {risk_score}, Advisories: {len(advisories)}, Route: {bool(route)}, RequestID: {req_display})")
    else:
        print(f"FAIL ({res.status_code}: {res.text})")
        failures.append("POST /plan failed")

    # 4. Trace retrieval
    print("[4/10] Testing GET /trace/{request_id} ...", end=" ")
    if request_id:
        res = client.get(f"/trace/{request_id}")
        if res.status_code == 200 and isinstance(res.json(), list) and len(res.json()) > 0:
            trace_nodes = [t.get("node_name") or t.get("agent") or "node" for t in res.json()]
            print(f"PASS ({' -> '.join(trace_nodes)})")
        else:
            print(f"FAIL ({res.status_code}: {res.text})")
            failures.append("GET /trace/{request_id} failed")
    else:
        print("SKIPPED (no request_id)")
        failures.append("GET /trace skipped due to /plan failure")

    # 4b. State retrieval
    print("[4b] Testing GET /state/{request_id} ...", end=" ")
    if request_id:
        res = client.get(f"/state/{request_id}")
        if res.status_code == 200 and "evidence" in res.json():
            s_data = res.json()
            print(f"PASS (Evidence: {len(s_data.get('evidence', []))}, Conflicts: {len(s_data.get('conflict_log', []))})")
        else:
            print(f"FAIL ({res.status_code}: {res.text})")
            failures.append("GET /state/{request_id} failed")
    else:
        print("SKIPPED (no request_id)")
        failures.append("GET /state skipped due to /plan failure")

    # 5. Non-existent Trace
    print("[5/10] Testing GET /trace/nonexistent (404 expected) ...", end=" ")
    res = client.get("/trace/nonexistent-trace-id-xyz")
    if res.status_code == 404:
        print("PASS (404 Not Found as expected)")
    else:
        print(f"FAIL (Expected 404, got {res.status_code})")
        failures.append("GET /trace 404 test failed")

    # 6. Start Voyage
    print("[6/10] Testing POST /voyages/start ...", end=" ")
    voyage_payload = {
        "location": {"lat": 18.922, "lon": 72.8346, "name": "Mumbai Port"},
        "voyage_id": "voyage-smoke-1"
    }
    res = client.post("/voyages/start", json=voyage_payload)
    voyage_id = None
    if res.status_code == 200:
        v_data = res.json()
        voyage_id = v_data.get("voyage_id")
        status = v_data.get("status")
        print(f"PASS (Voyage ID: {voyage_id}, Status: {status})")
    else:
        print(f"FAIL ({res.status_code}: {res.text})")
        failures.append("POST /voyages/start failed")

    # 7. Active Voyages
    print("[7/10] Testing GET /voyages/active ...", end=" ")
    res = client.get("/voyages/active")
    if res.status_code == 200 and isinstance(res.json(), list):
        active_ids = [v.get("voyage_id") for v in res.json()]
        if voyage_id in active_ids:
            print(f"PASS (Found active voyage {voyage_id} among {len(active_ids)} voyages)")
        else:
            print(f"FAIL (Voyage {voyage_id} not in active list: {active_ids})")
            failures.append("Active voyage list missing created voyage")
    else:
        print(f"FAIL ({res.status_code}: {res.text})")
        failures.append("GET /voyages/active failed")

    # 8. Trigger Alert
    print("[8/10] Testing POST /alerts/trigger ...", end=" ")
    alert_payload = {
        "voyage_id": voyage_id,
        "severity": "SEVERE",
        "headline": "Cyclone warning: Sea conditions rough to very rough",
        "advisory": {
            "authority": "IMD",
            "constraint_type": "NO_GO",
            "named_region": "Maharashtra Coast",
            "severity": "SEVERE",
            "valid_from": "2026-09-10T12:00:00Z",
            "valid_until": "2026-09-11T12:00:00Z",
            "source_text": "Fishermen are advised not to venture into Maharashtra Coast",
            "source_reference": "IMD-BULLETIN-01",
            "confidence": 0.95
        }
    }
    res = client.post("/alerts/trigger", json=alert_payload)
    if res.status_code == 200:
        alert_data = res.json()
        alerts_list = alert_data.get("alerts", [])
        if alerts_list:
            first_alert = alerts_list[0]
            safe_port = first_alert.get("safe_port", {}).get("name")
            dist = first_alert.get("safe_port", {}).get("distance_km", 0.0)
            print(f"PASS (Alert triggered: {first_alert.get('new_status')}, Safe Port: {safe_port} at {dist:.1f} km)")
        else:
            print(f"PASS (Alert evaluated: {alert_data.get('count', 0)} alerts)")
    else:
        print(f"FAIL ({res.status_code}: {res.text})")
        failures.append("POST /alerts/trigger failed")

    # 9. End Voyage
    print("[9/10] Testing POST /voyages/{id}/end ...", end=" ")
    if voyage_id:
        res = client.post(f"/voyages/{voyage_id}/end")
        if res.status_code == 200 and res.json().get("status") == "ended":
            print(f"PASS (Voyage {voyage_id} ended)")
        else:
            print(f"FAIL ({res.status_code}: {res.text})")
            failures.append("POST /voyages/{id}/end failed")
    else:
        print("SKIPPED")

    # 10. Voice Endpoints
    print("[10/10] Testing POST /voice/speak & /voice/transcribe ...", end=" ")
    tts_res = client.post("/voice/speak", json={"text": "समुद्र शांत आहे", "language": "mr-IN", "voice_id": "aditya"})
    if tts_res.status_code == 200 and tts_res.headers.get("content-type") == "audio/wav" and len(tts_res.content) > 0:
        wav_bytes = tts_res.content
        files = {"file": ("audio.wav", wav_bytes, "audio/wav")}
        data = {"language": "mr-IN"}
        stt_res = client.post("/voice/transcribe", files=files, data=data)
        if stt_res.status_code == 200 and "transcript" in stt_res.json():
            print(f"PASS (TTS generated {len(wav_bytes)} bytes WAV audio, STT transcript: '{stt_res.json().get('transcript')}')")
        else:
            print(f"FAIL STT ({stt_res.status_code}: {stt_res.text})")
            failures.append("POST /voice/transcribe failed")
    else:
        print(f"FAIL TTS ({tts_res.status_code}: {tts_res.text})")
        failures.append("POST /voice/speak failed")

    print("=" * 80)
    if failures:
        print(f"SMOKE TEST FAILED with {len(failures)} failures:")
        for f in failures:
            print(f"  - {f}")
        return 1
    print("ALL 10 API ENDPOINT CHECKS PASSED SUCCESSFULLY!")
    print("=" * 80)
    return 0

if __name__ == "__main__":
    sys.exit(run_smoke_test())
