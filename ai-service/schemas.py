"""
Shared schemas for ORCA's AI Agent Service.

The UIResponse shape below is a hard contract with the frontend (M5). The list of
allowed component `type` values must stay in sync with the frontend's component
registry (components.js) — do not add/remove types here without telling the
frontend developer.
"""

from typing import Any, Literal, Optional
from pydantic import BaseModel

ComponentType = Literal[
    "risk-card",
    "weather-card",
    "ocean-card",
    "pfz-card",
    "marine-map",
    "alert-card",
    "recommendation-card",
    "evidence-panel",
]


class UIComponent(BaseModel):
    type: ComponentType
    data: dict[str, Any]


class UIResponse(BaseModel):
    title: str
    components: list[UIComponent]


class Location(BaseModel):
    lat: float
    lon: float


class AgentRequest(BaseModel):
    query: str
    location: Location
    sessionId: Optional[str] = None


class AgentResponse(BaseModel):
    ui_json: UIResponse
    explanation_text: str
