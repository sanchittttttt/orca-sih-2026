"""
The single orchestrator function. No LangGraph — just a straight-line chain of
function calls, since the pipeline doesn't branch or loop in a way that needs
graph-based state management. See docs/ORCA_SESSION_HANDOFF_M4.md for the
full reasoning.
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

    # Deterministic risk score - only when we have both weather and ocean data
    if "weather" in evidence and "ocean" in evidence:
        try:
            wind = evidence["weather"]["current_weather"]["windspeed"]
            wave = evidence["ocean"]["current"]["wave_height"]
            rain = evidence["weather"]["hourly"]["precipitation_probability"][0]
            evidence["risk"] = tools.compute_risk_score(wind, wave, rain)
        except (KeyError, IndexError, TypeError):
            pass  # missing fields shouldn't crash the whole pipeline

    return evidence


def run_agent(query: str, lat: float, lon: float) -> dict:
    intent = classify_intent(query)
    plan = decide_what_data_is_needed(intent)
    evidence = gather_data(plan, lat, lon)
    explanation = explain_evidence(evidence)
    ui_json = build_ui(evidence, explanation)

    # Validate against the schema; fall back to a safe generic UI if it doesn't fit.
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
