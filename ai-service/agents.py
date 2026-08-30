"""
Four specialized agent functions. Each reasons about a specific part of the
problem and hands its output to the next — this is what makes the pipeline
genuinely agentic/multi-agent, independent of whether any orchestration
framework (LangGraph etc.) is used to wire them together. See
docs/ORCA_SESSION_HANDOFF_M4.md for the full reasoning behind this design
choice (deliberately NOT using LangGraph).

SAFETY RULE, enforced throughout this file: agents may only explain, select,
and arrange REAL data handed to them. They must never invent a risk score,
weather number, or PFZ coordinate themselves.
"""

import json
from llm_client import call_llm


def classify_intent(query: str) -> dict:
    """Agent 1: understand what the user is actually asking."""
    system = (
        "You classify a fisherman's question into exactly one intent category and "
        "extract any time reference mentioned. Respond ONLY with JSON, no other text: "
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
    over-engineering. Not every agent step needs to be an LLM call.
    """
    mapping = {
        "fishing_safety": {"weather": True, "ocean": True, "pfz": False, "alerts": True},
        "pfz_lookup": {"weather": False, "ocean": True, "pfz": True, "alerts": False},
        "route_planning": {"weather": True, "ocean": True, "pfz": False, "alerts": True},
        "general_info": {"weather": False, "ocean": False, "pfz": False, "alerts": False},
    }
    return mapping.get(intent.get("intent"), mapping["general_info"])


def explain_evidence(evidence: dict) -> str:
    """
    Agent 3: turn retrieved evidence into plain, calibrated language.

    Safety rule enforced in the prompt itself: never state an absolute
    safe/unsafe judgment, only describe the assessed risk level and evidence.
    """
    system = (
        "You explain marine safety data to a fisherman in plain, simple language. "
        "Rules you must follow: "
        "1) NEVER say a trip is definitely safe or unsafe - only describe the assessed "
        "risk level and the evidence behind it. "
        "2) NEVER invent numbers - only reference values present in the evidence given. "
        "3) Keep it to 2-4 short sentences."
    )
    return call_llm(system, json.dumps(evidence)).strip()


def build_ui(evidence: dict, explanation: str) -> dict:
    """
    Agent 4: select which fixed UI components apply and populate them with
    real values from the evidence. Never invents component types outside the
    fixed registry (that registry is a hard contract with the frontend).
    """
    system = (
        "You select which UI components to show based on the evidence given, and "
        "populate them using only the real values in that evidence - never invent "
        "numbers. You may ONLY use these component types, exactly as spelled: "
        "risk-card, weather-card, ocean-card, pfz-card, marine-map, alert-card, "
        "recommendation-card, evidence-panel. "
        "Respond ONLY with JSON in exactly this shape, no other text: "
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
