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
    system = (
        "You select which UI components to show based on the evidence given, and "
        "populate them using only the real values in that evidence - never invent "
        "numbers. You may ONLY use these component types, exactly as spelled, and each "
        "one's data object MUST use exactly these field names (omit a component "
        "entirely if you don't have its data, but never rename or restructure fields):\n"
        "- risk-card: {\"score\": number, \"level\": \"LOW\"|\"MODERATE\"|\"HIGH\"|\"EXTREME\"}\n"
        "- weather-card: {\"temperature_c\": number, \"windspeed_kmh\": number, "
        "\"winddirection_deg\": number, \"precipitation_probability\": number}\n"
        "- ocean-card: {\"wave_height_m\": number, \"wave_direction_deg\": number, "
        "\"wave_period_s\": number, \"sea_surface_temperature_c\": number}\n"
        "- pfz-card: {\"zones\": [{\"latitude\": number, \"longitude\": number, "
        "\"chlorophyll\": number, \"pfz_score\": number}]}\n"
        "- alert-card: {\"cyclone_alerts\": [...], \"lightning_alerts\": [...]} "
        "(pass the arrays through exactly as given in the evidence)\n"
        "- marine-map: {\"markers\": [{\"latitude\": number, \"longitude\": number, "
        "\"label\": string}]}\n"
        "- recommendation-card: {\"text\": string}\n"
        "- evidence-panel: for this ONE component type only, copy the ENTIRE evidence "
        "object given to you into the data field, with all its real keys and values - "
        "do NOT leave data empty, do NOT summarize it, copy it in full.\n"
        "Write a specific, informative title describing what was assessed - never use "
        "the generic word 'Assessment' alone.\n"
        "Respond ONLY with JSON in exactly this shape, no other text, no markdown, "
        "no code fences: "
        '{"title": "...", "components": [{"type": "...", "data": {...}}]}'
    )
    user = json.dumps({"evidence": evidence, "explanation": explanation})

    for attempt in range(2):  # try twice - a retry often lands on a different free model
        raw = call_llm(system, user, json_mode=True)
        print(f"[DEBUG] build_ui attempt {attempt + 1} raw response: {raw[:800]}")
        try:
            parsed = json.loads(raw)
            # Extra safety: catch the case where the model still returns an
            # empty evidence-panel despite the instruction, and patch it
            # ourselves rather than trusting the model got it right.
            for component in parsed.get("components", []):
                if component.get("type") == "evidence-panel" and not component.get("data"):
                    component["data"] = evidence
            return parsed
        except json.JSONDecodeError as e:
            print(f"[DEBUG] build_ui attempt {attempt + 1} JSON parse failed: {e}")
            continue

    return {
        "title": "Assessment",
        "components": [
            {"type": "recommendation-card", "data": {"text": explanation}},
            {"type": "evidence-panel", "data": evidence},
        ],
    }