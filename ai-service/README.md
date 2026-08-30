# ORCA AI Agent Service (Module 4)

Agentic AI reasoning layer for ORCA. Takes a natural-language marine query + a
location, reasons about what data is needed, retrieves it from real sources,
and returns a plain-language explanation plus structured UI JSON for the
frontend to render.

## Data — shared with Module 1, no duplication

This service reads directly from the top-level `../data/` folder — there is
only ONE copy of `pfz_points.json` and `lightning_alerts.json` in the whole
repo. Re-run `data/compute_pfz.py` whenever you want fresh PFZ zones; this
service picks up the new file automatically, no copying required. Weather,
marine, and cyclone data are called LIVE directly from Open-Meteo/GDACS —
nothing to keep in sync for those at all.

## Architecture — no LangGraph, on purpose

This is a plain Python function pipeline, not a graph-orchestration framework.
The pipeline runs in a straight line (classify → plan → fetch → explain →
build UI) and doesn't branch/loop in a way that needs LangGraph's state
management — a framework here would add a learning curve and a new failure
surface for no real benefit at this scale.

**This does not make the system less "agentic."** Being agentic is a behavior
— reasoning about what to do next, deciding which tools/data are needed,
specialized components handing off work to each other — not a specific
library. The four functions in `agents.py` are four genuine specialized
agents collaborating in sequence: Intent → Planner → Explanation → UI
Planning. See `docs/ORCA_SESSION_HANDOFF_M4.md` for the full reasoning.

## Files

- `schemas.py` — Pydantic models. `UIResponse` is the hard contract with the
  frontend's component registry — do not change the allowed `type` values
  without telling whoever owns the frontend.
- `llm_client.py` — OpenRouter client (free tier). Uses the `openrouter/free`
  auto-router model so the code doesn't break when OpenRouter's free-model
  catalogue rotates.
- `tools.py` — real data retrieval. Live calls to Open-Meteo (weather),
  Open-Meteo Marine (waves/SST), and GDACS (cyclones). Reads PFZ and
  lightning data from the shared `../data/` folder. Also has a **temporary**
  local copy of the fixed risk-scoring formula — replace with a REST call to
  the Risk/GIS service (Module 3) once that exists.
- `agents.py` — the four agent functions: `classify_intent`,
  `decide_what_data_is_needed`, `explain_evidence`, `build_ui`.
- `orchestrator.py` — `run_agent()`, chains everything together and validates
  the final output against the schema, falling back to a safe generic UI if
  validation fails.
- `main.py` — FastAPI app exposing `POST /ai/agent/run`.

## Setup

```bash
cd ai-service
python -m venv venv
venv\Scripts\activate      # Windows PowerShell
# or: source venv/bin/activate   # Git Bash / Mac / Linux

pip install -r requirements.txt
cp .env.example .env       # then add your real OpenRouter key
```

Get a free OpenRouter key at https://openrouter.ai (no card needed).

Make sure `../data/pfz_points.json` and `../data/lightning_alerts.json` exist
— run the scripts in `data/` first if they don't (see `data/README.md`).

## Run it

```bash
uvicorn main:app --reload --port 8000
```

## Test it

Health check:
```bash
curl http://localhost:8000/health
```

Real query:
```bash
curl -X POST http://localhost:8000/ai/agent/run \
  -H "Content-Type: application/json" \
  -d '{"query": "Is it safe to go fishing tomorrow?", "location": {"lat": 16.99, "lon": 73.31}}'
```

## Known constraints

- **OpenRouter free tier**: 50 requests/day, 20/min (1,000/day after the
  account has ever purchased $10 of credit). Don't loop/retry excessively
  while testing.
- **Safety rule enforced throughout**: the LLM only explains, selects, and
  arranges real data — it never invents a risk score, weather number, or PFZ
  coordinate. Enforced via the tool boundary (`tools.py` is the only place
  real numbers come from) and reinforced in every agent's system prompt.
- Once Module 3 (Risk/GIS Service) exists, replace `tools.compute_risk_score()`
  with a REST call to its `/internal/risk/score` endpoint, and replace
  `tools.get_nearest_pfz()`'s file read with a call to its
  `/internal/gis/nearest-pfz` endpoint.
