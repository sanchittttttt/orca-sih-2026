"""
The single orchestrator function — a straight-line chain of calls, no
LangGraph or other framework needed for a pipeline this shape.
"""

import tools
from agents import build_ui, classify_intent, decide_what_data_is_needed, explain_evidence
from schemas import UIResponse


def gather_data(plan: dict, lat: float, lon: float) -> dict:
    """Calls only the tools the planner decided are actually needed."""
    evidence: dict = {}

    if plan.get("weather"):
        try:
            evidence["weather"] = tools.fetch_weather(lat, lon)
        except Exception as e:
            evidence["weather_error"] = str(e)

    if plan.get("ocean"):
        try:
            evidence["ocean"] = tools.fetch_marine(lat, lon)
        except Exception as e:
            evidence["ocean_error"] = str(e)

    if plan.get("pfz"):
        evidence["nearest_pfz"] = tools.get_nearest_pfz(lat, lon)

    if plan.get("alerts"):
        evidence["cyclone_alerts"] = tools.get_cyclone_alerts()
        evidence["lightning_alerts"] = tools.get_lightning_alerts()

    if "weather" in evidence and "ocean" in evidence:
        try:
            wind = evidence["weather"]["current_weather"]["windspeed"]
            wave = evidence["ocean"]["current"]["wave_height"]
            rain = evidence["weather"]["hourly"]["precipitation_probability"][0]
            evidence["risk"] = tools.compute_risk_score(wind, wave, rain)
        except (KeyError, IndexError, TypeError):
            pass

    return evidence


import time

def run_agent(query: str, lat: float, lon: float) -> dict:
    t0 = time.time()
    intent = classify_intent(query)
    print(f"[TIMING] classify_intent: {time.time()-t0:.1f}s")

    t1 = time.time()
    plan = decide_what_data_is_needed(intent)
    evidence = gather_data(plan, lat, lon)
    print(f"[TIMING] gather_data (weather+marine+cyclone): {time.time()-t1:.1f}s")

    t2 = time.time()
    explanation = explain_evidence(evidence)
    print(f"[TIMING] explain_evidence: {time.time()-t2:.1f}s")

    t3 = time.time()
    ui_json = build_ui(evidence, explanation)
    print(f"[TIMING] build_ui: {time.time()-t3:.1f}s")

    # ... rest stays the same

    try:
        validated = UIResponse(**ui_json)
        ui_json_out = validated.model_dump()
    except Exception:
        ui_json_out = {
            "title": "Assessment",
            "components": [
                {"type": "recommendation-card", "data": {"text": explanation}},
                {"type": "evidence-panel", "data": evidence},
            ],
        }

    return {"ui_json": ui_json_out, "explanation_text": explanation}
