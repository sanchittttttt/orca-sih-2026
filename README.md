# ORCA — Marine EcOsystem Reasoning with Collaborative Agents
Smart India Hackathon 2026 — PS 26176 (ISRO)

Agentic AI conversational marine intelligence platform for fishermen, researchers,
disaster management agencies, and maritime operators.

## Structure
- `backend-core/` — Spring Boot: auth, chat, orchestration, SSE
- `risk-gis-service/` — Spring Boot + PostGIS: deterministic risk scoring, geofencing
- `ai-service/` — Python + FastAPI: agent orchestration, UI JSON generation
- `frontend/` — Vanilla JS + Leaflet: generative UI + map
- `data/` — dataset fetch scripts and snapshots (single source of truth — ai-service
  reads directly from here, no duplicated copies)
- `docs/` — architecture diagrams, module playbook, session handoffs, SIH presentation content

## Status (as of this snapshot)
- **M1 (Dataset)**: done — weather, marine/SST, chlorophyll, PFZ computation, cyclone
  alerts, lightning mock, all documented in `data/DATA_SOURCES.md`. Boundaries/MPA
  deferred as a stretch goal.
- **M4 (AI Agent Service)**: working end-to-end pipeline (intent → plan → gather data →
  explain → build UI), tested with mocked LLM/API calls. Not yet tested against the real
  OpenRouter API or live in a real run.
- **M2, M3, M5**: not started.

See `docs/ORCA_Module_Breakdown_and_Playbook.md` for full module specs and API contracts,
and `docs/ORCA_SESSION_HANDOFF_M4.md` for the detailed reasoning behind decisions made
while building M1 and M4.

## How to run the AI service locally
See `ai-service/README.md`.
