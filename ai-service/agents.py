"""
Four specialized agent functions, each reasoning about a specific part of the
problem and handing its output to the next. This is what makes the pipeline
genuinely agentic — independent of any orchestration framework being used.

SAFETY RULE enforced throughout: agents may only explain, select, and arrange
REAL data handed to them. They must never invent a risk score, weather
number, or PFZ coordinate.
"""

import json
from llm_client import call_llm


def classify_intent(query: str) -> dict:
    """Agent 1: understand what the user is actually asking."""
    system = (
        "You classify a fisherman's question into exactly one intent category and "
        "extract any time reference mentioned. Respond ONLY with JSON, no other text, "
        "no markdown formatting, no code fences: "
        '{"intent": "fishing_safety" | "pfz_lookup" | "route_planning" | "general_info", '
        '"time_reference": "today" | "tomorrow" | "this_week" | "unspecified"}'
    )
    raw = call_llm(system, query, json_mode=True)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {"intent": "general_info", "time_reference": "unspecified"}


def decide_what_data_is_needed(intent: dict) -> dict:
    """
    Agent 2 (planner): decide which data sources this query needs.

    Deliberately plain logic, not an LLM call — the mapping from intent to
    needed sources is small and fixed enough that reasoning here would be
    over-engineering. The agentic part is dynamically deciding which sources
    apply to THIS query, not the mechanism used to decide.
    """
    mapping = {
        "fishing_safety": {"weather": True, "ocean": True, "pfz": False, "alerts": True},
        "pfz_lookup": {"weather": False, "ocean": True, "pfz": True, "alerts": False},
        "route_planning": {"weather": True, "ocean": True, "pfz": False, "alerts": True},
        "general_info": {"weather": False, "ocean": False, "pfz": False, "alerts": False},
    }
    return mapping.get(intent.get("intent"), mapping["general_info"])


def explain_evidence(evidence: dict) -> str:
    system = (
        "You explain marine safety data to a fisherman in plain, simple language. "
        "STRICT RULE: you are FORBIDDEN from using the words 'safe', 'unsafe', "
        "'safety', or 'dangerous' anywhere in your response. Instead, always describe "
        "the assessed risk LEVEL (LOW/MODERATE/HIGH/EXTREME) and the specific evidence "
        "behind it - for example say 'conditions are assessed as LOW RISK based on "
        "current wind and wave data' instead of saying anything is safe or unsafe. "
        "NEVER invent numbers - only reference values present in the evidence given. "
        "Keep it to 2-4 short sentences. Respond with plain text only."
    )
    result = call_llm(system, json.dumps(evidence)).strip()

    # Backstop: if the model ignores the instruction anyway, catch it here
    forbidden = ["unsafe", "safe", "safety", "dangerous"]
    if any(word in result.lower() for word in forbidden):
        risk = evidence.get("risk", {})
        level = risk.get("level", "UNKNOWN")
        return (
            f"Conditions are currently assessed as {level} RISK based on available "
            f"weather and ocean data. Review the details below before deciding."
        )

    return result


def build_ui(evidence: dict, explanation: str) -> dict:
    """
    Agent 4: select which fixed UI components apply and populate them with
    real values from the evidence. Never invents component types outside the
    fixed registry (a hard contract with the frontend).
    """
    system = (
        "You select which UI components to show based on the evidence given, and "
        "populate them using only the real values in that evidence - never invent "
        "numbers. You may ONLY use these component types, exactly as spelled: "
        "risk-card, weather-card, ocean-card, pfz-card, marine-map, alert-card, "
        "recommendation-card, evidence-panel. "
        "Respond ONLY with JSON in exactly this shape, no other text, no markdown, "
        "no code fences: "
        '{"title": "...", "components": [{"type": "...", "data": {...}}]}'
    )
    user = json.dumps({"evidence": evidence, "explanation": explanation})
    raw = call_llm(system, user, json_mode=True)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "title": "Assessment",
            "components": [
                {"type": "recommendation-card", "data": {"text": explanation}},
                {"type": "evidence-panel", "data": evidence},
            ],
        }
