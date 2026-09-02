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


def _format_history(history: list[dict] | None, max_turns: int = 6) -> str:
    """Turns the last few messages into plain text for prompt context."""
    if not history:
        return ""
    recent = history[-max_turns:]
    lines = [f"{h['role']}: {h['content']}" for h in recent]
    return "\n".join(lines)


def classify_intent(query: str, history: list[dict] | None = None) -> dict:
    system = (
        "You classify a fisherman's question into exactly one intent category and "
        "extract any time reference mentioned. You may be given prior conversation "
        "history for context - use it to resolve vague follow-up questions like "
        "'what about tomorrow' or 'the day after' by inferring they continue the same "
        "topic as the most recent relevant prior message. Always classify based on the "
        "CURRENT message's ultimate intent, using history only to fill in what's implied "
        "but not restated. Respond ONLY with JSON, no other text, no markdown formatting, "
        "no code fences: "
        '{"intent": "fishing_safety" | "pfz_lookup" | "route_planning" | "hazard_alert" | "general_info", '
        '"time_reference": "today" | "tomorrow" | "this_week" | "unspecified"}\n'
        "Use hazard_alert specifically for questions about cyclones, storms, lightning, "
        "or active warnings/alerts - NOT general_info - even if fishing isn't mentioned."
    )

    history_text = _format_history(history)
    user_prompt = (
        f"Conversation history:\n{history_text}\n\nCurrent message: {query}"
        if history_text
        else query
    )

    raw = call_llm(system, user_prompt, json_mode=True)
    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        result = {"intent": "general_info", "time_reference": "unspecified"}

    query_lower = query.lower()

    pfz_keywords = [
        "pfz", "productive fishing zone", "fishing zone", "fishing zones",
        "good fishing spot", "good fishing spots", "fish zone", "fish zones",
        "nearby fishing", "nearest fishing", "fishing near me", "fishing zones near me",
        "where are the fish", "where are the fishing zones", "productive zone"
    ]
    weather_keywords = [
        "weather", "how is the weather", "what is the weather", "weather conditions",
        "wind", "rain", "clouds", "forecast", "temperature", "humidity", "sea state"
    ]
    hazard_keywords = ["cyclone", "storm", "lightning", "alert", "warning", "hazard"]

    if any(keyword in query_lower for keyword in pfz_keywords):
        result["intent"] = "pfz_lookup"
        return result

    if any(keyword in query_lower for keyword in weather_keywords):
        result["intent"] = "fishing_safety"
        return result

    if result.get("intent") == "general_info" and any(k in query_lower for k in hazard_keywords):
        result["intent"] = "hazard_alert"

    return result


def decide_what_data_is_needed(intent: dict) -> dict:
    mapping = {
        "fishing_safety": {"weather": True, "ocean": True, "pfz": False, "alerts": True},
        "pfz_lookup": {"weather": False, "ocean": True, "pfz": True, "alerts": False},
        "route_planning": {"weather": True, "ocean": True, "pfz": False, "alerts": True},
        "hazard_alert": {"weather": False, "ocean": False, "pfz": False, "alerts": True},
        "general_info": {"weather": False, "ocean": False, "pfz": False, "alerts": False},
    }
    return mapping.get(intent.get("intent"), mapping["general_info"])


def explain_evidence(evidence: dict, history: list[dict] | None = None) -> str:
    """
    Agent 3: turn retrieved evidence into plain, calibrated language.
    Never states an absolute safe/unsafe judgment, never invents numbers.

    History is passed through here too so the explanation can read naturally
    as a continuation ("compared to yesterday...") rather than repeating
    itself as if this were the first message — optional context, not required
    for correctness.
    """
    system = (
        "You explain marine safety data to a fisherman in plain, simple language. "
        "You may be given prior conversation history for tone/continuity context only - "
        "the evidence given to you is always about the CURRENT question, not the past one. "
        "Rules you must follow: "
        "1) NEVER say a trip is definitely safe or unsafe - only describe the assessed "
        "risk level and the evidence behind it. "
        "2) NEVER invent numbers - only reference values present in the evidence given. "
        "3) Keep it to 2-4 short sentences. "
        "4) Respond with plain text only, no JSON, no markdown."
    )
    history_text = _format_history(history, max_turns=2)
    user_prompt = (
        f"Recent conversation for context:\n{history_text}\n\nCurrent evidence:\n{json.dumps(evidence)}"
        if history_text
        else json.dumps(evidence)
    )

    result = call_llm(system, user_prompt).strip()

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