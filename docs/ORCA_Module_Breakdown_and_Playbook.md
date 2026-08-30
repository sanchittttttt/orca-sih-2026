# ORCA — Module Breakdown & Team Playbook
### SIH Problem Statement 26176 — Marine EcOsystem Reasoning with Collaborative Agents (ISRO)

This document is the single source of truth for how ORCA is split into modules, who owns what,
what tech stack each module uses, how modules talk to each other, how we manage the GitHub repo,
and what content the documentation/PPT module needs to collect from everyone else.

Each module section below has a **"Context for another LLM"** block — copy that block verbatim
into a fresh chat with any LLM to get instant, accurate context for working on that module alone.

---

## 1. Team & Module Map

| # | Module | Owner | Core Tech |
|---|---|---|---|
| M1 | Dataset & Data Integration | Teammate E (limited condition) | Python scripts, static JSON/GeoJSON, Open-Meteo, Copernicus Marine, GDACS |
| M2 | Backend Core Service | Spring Boot Dev #1 | Java, Spring Boot, PostgreSQL, JPA, SSE |
| M3 | Risk Engine & GIS Service | Spring Boot Dev #2 | Java, Spring Boot, PostGIS, Hibernate Spatial |
| M4 | AI Agent Orchestration | Python/AI Dev | Python, FastAPI, LangGraph, LLM (structured output) |
| M5 | Frontend — Generative UI + Map | Frontend Dev | Vanilla HTML/CSS/JS, Leaflet |
| M6 | Documentation & PPT | Teammate F (limited condition) | Markdown, Google Slides/PPT, draw.io/Excalidraw |

Teammates E and F should sync daily — E's dataset outputs are the evidence F needs for the
"Prototype & Reference Links" and "Technical Approach" slides.

---

## 2. Module 1 — Dataset & Data Integration

**Goal:** Provide every other module with clean, reliable data — either real (fetched live) or
realistically simulated — with zero ambiguity about which is which.

**Tech stack:** Python (requests, pandas), `copernicusmarine` pip package, static JSON/GeoJSON files, cron-style script (can just be run manually before demo).

**Responsibilities:**
- Write/run a script that calls **Open-Meteo** (weather) and **Open-Meteo Marine** (waves/ocean temp) for a given lat/lon — no API key needed.
- Register for **Copernicus Marine**, use the `copernicusmarine` Python toolbox to subset chlorophyll data for a bounding box around the Indian coast (e.g. 8°N–22°N, 68°E–90°E) once, export as CSV, hand to M3/M4.
- Call **GDACS** API for active tropical cyclone alerts, filter to the India region.
- Download static GeoJSON once for Indian maritime boundaries / Marine Protected Areas (Marine Regions, Protected Planet) and hand to M3 for PostGIS loading.
- Build the **mock PFZ dataset**: a few dozen realistic lat/lon points off the Indian coast, computed by applying INCOIS's real threshold method (SST fronts + chlorophyll concentration) to the real SST + chlorophyll data above — not random numbers.
- Build a small **mock lightning-alert dataset** (no free real API found) — a simple JSON of active/no-active alerts per region.
- Document exactly which fields are live vs. simulated, and why, in a `DATA_SOURCES.md` — this feeds directly into M6.

**Outputs (→ who consumes them):**
- `weather_snapshot.json`, `marine_snapshot.json` → M4 (agent tool calls)
- `chlorophyll_snapshot.csv` → M3 (loaded into Postgres table)
- `pfz_points.json` → M3 (loaded into PostGIS)
- `boundaries.geojson`, `mpa.geojson` → M3 (loaded into PostGIS)
- `cyclone_alerts.json`, `lightning_alerts.json` → M4
- `DATA_SOURCES.md` → M6

**Context for another LLM:**
```
You are working on the Dataset & Data Integration module for ORCA, a Smart India Hackathon
project (PS 26176, ISRO) — an agentic AI conversational marine intelligence platform for
Indian fishermen/coastal stakeholders. Your job is NOT to build agents or UI — only to fetch,
clean, and package marine/weather data for other modules to consume.

Use these confirmed-real, free APIs:
- Open-Meteo (weather: wind, rain, temp) — no key needed, https://api.open-meteo.com/v1/forecast
- Open-Meteo Marine (waves, swell, ocean temp) — no key needed, https://marine-api.open-meteo.com/v1/marine
- Copernicus Marine (chlorophyll, SST) — free registration required, use the `copernicusmarine`
  Python package to subset data to CSV for a bounding box around the Indian coast
- GDACS (cyclone alerts globally, including India) — free, keyless, https://www.gdacs.org/gdacsapi/

INCOIS (the real Indian government PFZ source) has NO public REST API — it only publishes via
WebGIS and SMS. So: compute a PFZ dataset yourself by applying INCOIS's real published method
(SST fronts + chlorophyll threshold) to the real SST/chlorophyll data you pulled above. This is
not "faking data" — it's implementing the real method with real inputs. Only truly mock what has
no real source at all (lightning alerts specifically).

Output plain JSON/CSV/GeoJSON files with clear filenames. Document which fields are live vs.
simulated in DATA_SOURCES.md. Other modules (Spring Boot backend, Python AI agents) will consume
your output files directly — keep formats simple and consistent.
```

---

## 3. Module 2 — Backend Core Service

**Goal:** Single entry point for the frontend. Owns auth, users, chat sessions, and streams
responses back to the browser.

**Tech stack:** Java, Spring Boot, Spring Web, Spring Data JPA, PostgreSQL, Server-Sent Events (SSE).

**Responsibilities:**
- `POST /api/auth/login`, `/api/auth/register` — basic auth (JWT is fine, don't over-engineer).
- `POST /api/chat` — accepts user's natural-language query + location, forwards to M4 (AI service), streams the response back via SSE.
- `GET /api/conversations` — chat history per user.
- Persist users, chat sessions, and messages in Postgres via JPA.
- Acts as the **only** service the frontend talks to — it internally calls M3 (risk/GIS) and M4 (AI agents) over REST, so the frontend never needs to know about the Python service.

**Inputs:** HTTP requests from Frontend (M5).
**Outputs:** SSE stream of `{type: "status" | "ui_json" | "text", data: ...}` events back to Frontend; REST calls out to M4's `/ai/agent/run`.

**Context for another LLM:**
```
You are building the Backend Core Service for ORCA (SIH PS 26176, ISRO marine intelligence
platform). Stack: Java, Spring Boot, Spring Data JPA, PostgreSQL, SSE.

Your service is the ONLY thing the frontend talks to directly. Responsibilities: auth
(JWT-based, keep it simple), user/chat-session persistence in Postgres, and a `/api/chat`
endpoint that:
1. Receives {query: string, location: {lat, lon}, sessionId: string} from the frontend
2. Calls the Python AI service at POST /ai/agent/run with the same payload
3. That Python service returns structured JSON: {ui_json: {...}, explanation_text: string}
4. You persist the exchange to Postgres and stream the result back to the frontend via SSE
   as progressive events (e.g. {"type":"status","message":"Checking weather..."} then
   {"type":"result","ui_json":{...},"text":"..."})

You also expose thin proxy endpoints the frontend map uses: GET /api/geofences,
GET /api/pfz (these actually call the Risk/GIS service — Module 3 — internally).

Do NOT put risk-scoring math or geospatial queries here — that's a separate service
(Module 3) reachable at http://risk-gis-service:8081 internally. Your job is orchestration,
auth, and persistence only.
```

---

## 4. Module 3 — Risk Engine & GIS Service

**Goal:** All deterministic, safety-critical math and spatial queries live here. The LLM never
touches these numbers — it only explains them.

**Tech stack:** Java, Spring Boot, PostgreSQL + PostGIS, Hibernate Spatial.

**Responsibilities:**
- Load M1's `pfz_points.json`, `boundaries.geojson`, `mpa.geojson`, `chlorophyll_snapshot.csv` into PostGIS tables on startup.
- `POST /internal/risk/score` — takes `{wind, waveHeight, rainProbability, lightningLevel, cycloneLevel, tideState}` → returns `{score: 0-100, level: "LOW"|"MODERATE"|"HIGH"|"EXTREME", breakdown: {...}}` using a fixed weighted formula (see below).
- `GET /internal/gis/nearest-pfz?lat=&lon=` → nearest PFZ point(s) using `ST_Distance`.
- `GET /internal/gis/geofence-check?lat=&lon=` → whether the point is inside a restricted/MPA polygon using `ST_Contains`/`ST_Intersects`.
- `POST /internal/route/safe-route` *(stretch goal)* — A*/Dijkstra over a cost grid.

**Risk formula (fixed, deterministic — do not let the LLM invent this):**
```
score = windScore*0.25 + waveScore*0.25 + rainScore*0.15 + lightningScore*0.15 + cycloneScore*0.20
0–30 LOW · 31–60 MODERATE · 61–80 HIGH · 81–100 EXTREME
```

**Inputs:** Called internally by M2 and M4 (never directly by the frontend).
**Outputs:** JSON risk scores, nearest-PFZ results, geofence booleans.

**Context for another LLM:**
```
You are building the Risk Engine & GIS Service for ORCA (SIH PS 26176, ISRO). Stack: Java,
Spring Boot, PostgreSQL + PostGIS, Hibernate Spatial.

This is a deterministic, internal-only service — no LLM involvement, no natural language.
It is called by the Backend Core Service (Java, Spring Boot) and the AI Agent Orchestration
service (Python, FastAPI) over plain REST.

Core principle: safety-critical numbers must NEVER be invented by an LLM. You own:
1. Risk scoring: POST /internal/risk/score — input is raw sensor/forecast values (wind km/h,
   wave height m, rain probability %, lightning level, cyclone level, tide state), output is
   a fixed weighted score 0-100 mapped to LOW/MODERATE/HIGH/EXTREME using this exact formula:
   score = windScore*0.25 + waveScore*0.25 + rainScore*0.15 + lightningScore*0.15 + cycloneScore*0.20
2. GIS queries: GET /internal/gis/nearest-pfz (uses ST_Distance on a PFZ points table) and
   GET /internal/gis/geofence-check (uses ST_Contains/ST_Intersects against restricted-zone
   and Marine-Protected-Area polygons).

Data comes from the Dataset module as pfz_points.json, boundaries.geojson, mpa.geojson,
chlorophyll_snapshot.csv — write a startup loader that ingests these into PostGIS tables
(geometry columns, SRID 4326).

Keep this service boring and correct — it's the safety backbone others rely on.
```

---

## 5. Module 4 — AI Agent Orchestration

**Goal:** Understand the user's query, plan which data to fetch, call the right agents/tools,
and produce structured UI JSON + a natural-language explanation — never inventing numbers itself.

**Tech stack:** Python, FastAPI, LangGraph, an LLM with structured/tool-calling output, Pydantic for schema validation.

**Responsibilities:**
- `POST /ai/agent/run` — receives `{query, location, sessionId}` from M2.
- **Intent Agent**: classify intent (fishing-safety / PFZ-lookup / route-planning / general-info), extract location + time, detect language.
- **Planner Agent**: decide which of the following are needed for this query: weather, ocean conditions, PFZ, alerts, geofencing, route.
- **Tool calls**: hit M1's data files/M3's REST endpoints for weather, ocean, risk score, nearest PFZ, geofence check, cyclone/lightning alerts.
- **Explanation Agent**: turn the retrieved evidence into a natural-language, non-absolute recommendation (e.g. "conditions are assessed as MODERATE RISK" — never "yes it's safe").
- **UI Planning Agent**: pick which fixed UI components apply (RiskCard, WeatherCard, OceanCard, PFZCard, MarineMap, AlertCard, RecommendationCard, EvidencePanel) and populate their data — output validated against a Pydantic schema before returning.
- Retry once on schema-validation failure; fall back to a generic RecommendationCard + EvidencePanel if it still fails, so the UI never breaks.

**Inputs:** REST call from M2; data from M1 files and M3 endpoints.
**Outputs:** `{ui_json: {title, components: [...]}, explanation_text: string}` back to M2.

**Context for another LLM:**
```
You are building the AI Agent Orchestration service for ORCA (SIH PS 26176, ISRO marine
intelligence platform). Stack: Python, FastAPI, LangGraph, an LLM with tool-calling/structured
output, Pydantic.

You expose one endpoint: POST /ai/agent/run, called internally by the Spring Boot backend.
Input: {query: string, location: {lat, lon}, sessionId: string}.

Your pipeline: Intent Agent (classify intent + extract location/time/language) → Planner Agent
(decide which of: weather, ocean, PFZ, alerts, geofencing, route are needed) → call tools for
each needed piece of data (weather/ocean come from local JSON files or a thin wrapper around
Open-Meteo; risk score, nearest-PFZ, and geofence checks come from REST calls to the Risk/GIS
service at http://risk-gis-service:8081/internal/...) → Explanation Agent (turn evidence into
plain-language, NEVER-absolute wording, e.g. "conditions are assessed as MODERATE RISK based on
available data" not "yes it's safe") → UI Planning Agent (select from this FIXED component
registry only: RiskCard, WeatherCard, OceanCard, PFZCard, MarineMap, AlertCard,
RecommendationCard, EvidencePanel — never invent new component types).

CRITICAL SAFETY RULE: you must never invent a risk score, PFZ coordinate, or weather number
yourself — always retrieve it from a tool call. Your job is planning, tool selection, and
turning retrieved data into explanation + UI composition.

Output must validate against this Pydantic schema before returning:
{ "title": str, "components": [ {"type": str, "data": dict} ] }
On validation failure, retry generation once; if it fails again, return a fallback
RecommendationCard + EvidencePanel so the frontend never gets a broken response.
```

---

## 6. Module 5 — Frontend: Generative UI + Map

**Goal:** Render whatever UI JSON the backend sends, via a fixed component registry — never
execute arbitrary code from the LLM.

**Tech stack:** Vanilla HTML, CSS, JavaScript, Leaflet (or MapLibre) for maps.

**Responsibilities:**
- Chat interface: input box, message history, connects to M2's `/api/chat` via SSE (`EventSource`).
- Component registry (`components.js`): one render function per UI JSON component type — `RiskCard`, `WeatherCard`, `OceanCard`, `PFZCard`, `MarineMap`, `AlertCard`, `RecommendationCard`, `EvidencePanel`. Matches M4's registry exactly — **keep these two lists in sync, this is the #1 integration risk.**
- Renderer (`renderer.js`): takes the UI JSON from an SSE event, clears the canvas, calls the matching render function per component.
- Map (`map.js`): Leaflet map with toggleable layers — PFZ points, restricted zones/MPA polygons, current location — fetched from M2's `/api/pfz` and `/api/geofences` proxy endpoints.
- Loading/error states: while SSE events are streaming in ("Checking weather...", "✓ Weather retrieved"), and a graceful fallback UI if the backend returns nothing renderable.

**Inputs:** SSE stream from M2.
**Outputs:** None (leaf of the pipeline) — but its component-type list is a hard contract with M4.

**Context for another LLM:**
```
You are building the frontend for ORCA (SIH PS 26176, ISRO marine intelligence platform).
Stack: Vanilla HTML/CSS/JS (no framework), Leaflet for maps. No React.

You connect to a Spring Boot backend's POST /api/chat endpoint and listen to Server-Sent
Events for the response. Events look like:
{"type":"status","message":"Checking weather..."}
{"type":"result","ui_json":{"title":"...","components":[{"type":"risk-card","data":{...}}]},"text":"..."}

Build a component registry (components.js) with one render function per type. The FIXED set of
component types you must support (this list is a strict contract with the backend AI service —
do not add/remove types without telling them): risk-card, weather-card, ocean-card, pfz-card,
marine-map, alert-card, recommendation-card, evidence-panel.

renderer.js: on receiving a "result" event, clear the #canvas div and call the matching render
function for each component in ui_json.components, in order. If a component type isn't in your
registry, skip it silently (don't crash the whole UI over one bad component).

Build a Leaflet map (map.js) with toggleable layers for PFZ points and restricted-zone/MPA
polygons, fetched from GET /api/pfz and GET /api/geofences on the Spring Boot backend.

Show progressive "status" messages while waiting, and always have a fallback empty-state UI
if no components come back.
```

---

## 7. Module 6 — Documentation & PPT

**Goal:** Own the SIH presentation and all supporting docs. Pull real content from every module
owner rather than writing generic filler — judges can tell the difference.

**Tech stack:** Google Slides or PowerPoint, Excalidraw/draw.io for diagrams, Markdown for internal docs.

Your target format is the **standard 6-slide SIH structure** (confirmed from a past winning
team's deck, "$BLACKGOLD$", PS 1646, SIH 2024). Match this structure exactly:

### Slide 1 — Title Page
Pull from: team lead. Needs: PS ID (26176), PS Title (ORCA — Marine EcOsystem Reasoning with
Collaborative Agents), Theme, PS Category (Software), Team ID, Team Name.

### Slide 2 — Our Solution
Pull from: whoever owns the overall pitch, informed by M2–M5.
Needs:
- 2-3 sentence proposed solution ("ORCA doesn't just answer marine questions — it autonomously
  reasons across ocean, weather, satellite, and geospatial data and generates the right
  interactive interface for every marine decision")
- A **flowchart** of the core user flow: ask each module owner for their step (Intent → Planner
  → Weather/Ocean/PFZ/Alert Agents → Risk Engine → Explanation → UI Generation → Render). This
  mirrors the flowchart style in the reference deck (boxes + arrows + decision diamonds).
- Main Benefits (2-4 bullets): e.g. explainable risk scoring, multilingual support, adaptive UI
- Innovative Features: conversational multi-agent reasoning, generative UI, deterministic
  safety-critical scoring, geofencing alerts

### Slide 3 — Technical Approach
Pull from: **every module owner must fill in their own subsection.** Needs:
- Platform & architecture diagram (see Section 9 below for exact boxes/arrows to draw)
- Tech stack tiles (mirror the reference deck's logo-grid style): Spring Boot, PostgreSQL,
  PostGIS, Python, FastAPI, LangGraph, Leaflet, HTML5/CSS3/JS — ask M2–M5 owners for their
  exact stack line so nothing is misrepresented
- AI/ML integration section: intent classification, structured-output UI generation, deterministic
  risk formula (state explicitly that risk scores are NOT LLM-generated — judges from ISRO will
  likely ask this directly, so pre-empt it)
- Security/auth notes from M2 (JWT-based auth, etc. — keep accurate to what's actually built)

### Slide 4 — Impact and Benefits
Pull from: team discussion, informed by the original PS's stated stakeholders (fishermen,
disaster management, researchers, maritime operators, authorities). Needs:
- Impacts: fisherman safety, faster PFZ discovery, disaster-alert timeliness, explainable
  decision support, multilingual accessibility
- Benefits: reduced fuel/time cost searching for fish, fewer at-sea safety incidents, faster
  hazard awareness
- Innovative points: multi-agent collaboration, generative UI, deterministic safety layer
- (Optional) a benefits diagram in the same tree/branch style as the reference deck

### Slide 5 — Feasibility and Viability
Pull from: **be honest here** — this is where M1's DATA_SOURCES.md matters most. Needs:
- Technical feasibility: which data is live (Open-Meteo, Open-Meteo Marine, GDACS, Copernicus
  Marine) vs. simulated-with-real-methodology (PFZ, lightning) — state this plainly, don't hide it
- Cost efficiency: all core APIs used are free/no-key or free-tier
- Risks & mitigation: LLM hallucination (mitigated via deterministic Risk Engine + schema
  validation), data availability (mitigated via cached/pre-fetched snapshots, not live per-query
  calls to slow sources like Copernicus)
- Ease of implementation: modular multi-agent architecture, mock-first progressive development

### Slide 6 — Prototype & Reference Links
Pull from: everyone. Needs:
- Demo video link (record once the core flow works end-to-end)
- Reference links: INCOIS PFZ Advisory page, Open-Meteo docs, Copernicus Marine, GDACS docs,
  the official SIH PS page — same style as the reference deck's "Reference Links" section

**Context for another LLM:**
```
You are building the SIH presentation deck for ORCA (PS 26176, ISRO — Marine EcOsystem
Reasoning with Collaborative Agents). Follow the standard 6-slide SIH format exactly:
1. Title Page (PS ID, Title, Theme, Category, Team ID, Team Name)
2. Our Solution (proposed solution + flowchart of the user query flow + benefits + innovative
   features)
3. Technical Approach (architecture diagram + tech stack grid + AI/ML integration notes +
   security notes)
4. Impact and Benefits (impacts + benefits + innovative points, ideally with a simple tree/branch
   diagram)
5. Feasibility and Viability (technical feasibility, cost efficiency, risks & mitigation, ease
   of implementation)
6. Prototype & Reference Links (demo video + citation links to real data sources used)

ORCA's actual architecture: Frontend (vanilla JS + Leaflet) → Spring Boot backend (auth, chat,
orchestration, SSE) → Python FastAPI + LangGraph AI service (intent → planning → specialized
agents → explanation → UI JSON) → a separate deterministic Risk Engine + PostGIS GIS service
(Spring Boot) for all safety-critical scoring and geofencing — the LLM never invents risk scores.

Real data sources used: Open-Meteo (weather, free/keyless), Open-Meteo Marine (waves/ocean
temp, free/keyless), Copernicus Marine (chlorophyll/SST, free with registration), GDACS
(cyclone alerts, free/keyless). PFZ zones are computed (not randomly faked) by applying
INCOIS's real published method (SST fronts + chlorophyll threshold) to this real data, because
INCOIS itself has no public API. Lightning alerts are simulated since no free real-time source
exists for India specifically — state this honestly on the feasibility slide rather than
hiding it.

Ask each module owner for their specific tech stack line, their part of the architecture
diagram, and their honest feasibility notes rather than inventing generic content — a deck
built from real module details is much stronger than generic hackathon-pitch language.
```

---

## 8. GitHub Repository Management

**Structure: one monorepo** (simpler coordination for a hackathon team than multi-repo):

```
orca-sih2026/
├── backend-core/          (M2 - Spring Boot)
├── risk-gis-service/      (M3 - Spring Boot)
├── ai-service/            (M4 - Python/FastAPI)
├── frontend/              (M5 - Vanilla JS)
├── data/                  (M1 - datasets, fetch scripts, DATA_SOURCES.md)
├── docs/                  (M6 - architecture diagrams, notes feeding the PPT)
├── docker-compose.yml     (spins up Postgres+PostGIS, Redis if used, all services)
└── README.md              (top-level: how to run everything locally)
```

**Branching:**
- `main` — protected, always demo-able. No direct pushes.
- One feature branch per module per task: `feature/m2-chat-endpoint`, `feature/m3-risk-formula`, `feature/m4-intent-agent`, `feature/m5-map-layers`, `feature/m1-copernicus-fetch`.
- PR into `main` requires at least one other person's review — pair Spring Boot devs to review each other's PRs (M2↔M3), and have the AI/Frontend devs review each other's integration points (M4↔M5) since that's the riskiest contract (UI component types must match exactly).

**Commit convention (Conventional Commits, keep it light):**
`feat(m3): add risk scoring endpoint`, `fix(m5): correct SSE event parsing`, `docs(m6): add architecture diagram notes`

**Project board columns:** `Backlog` → `In Progress` → `In Review` → `Done`. One card per module responsibility listed in Sections 2-7 above — this doubles as your task tracker.

**.gitignore essentials:** `.env`, `node_modules/`, `target/` (Java), `__pycache__/`, `*.pyc`, `.venv/`, any Copernicus/API credentials.

**Per-module README:** Each of the 5 code folders (`backend-core`, `risk-gis-service`, `ai-service`, `frontend`, `data`) needs its own short README with: what it does, how to run it locally, and its API contract (inputs/outputs) — this is what makes independent parallel development actually work without constant Slack pings.

---

## 9. Integration Map — How Everything Connects

End-to-end flow for a query like *"Can I go fishing tomorrow morning from Ratnagiri?"*:

1. **Frontend (M5)** sends `POST /api/chat {query, location, sessionId}` to **Backend Core (M2)**, opens an SSE connection for the response.
2. **M2** persists the message, forwards the same payload to **AI Service (M4)** via `POST /ai/agent/run`.
3. **M4**'s Intent Agent classifies intent + extracts time/location; Planner Agent decides which data is needed.
4. **M4** calls **Risk/GIS Service (M3)** internally: `POST /internal/risk/score`, `GET /internal/gis/nearest-pfz`, `GET /internal/gis/geofence-check` — plus reads weather/ocean/cyclone data from **M1**'s snapshot files.
5. **M4**'s Explanation + UI Planning Agents produce `{ui_json, explanation_text}`, validated against the shared Pydantic/JSON schema.
6. **M4** returns this to **M2**, which streams it to **M5** via SSE.
7. **M5**'s renderer matches each `ui_json.components[].type` against its component registry and draws the UI.

**The single hardest integration point:** the list of UI component `type` strings must be
*identical* between M4 (who generates them) and M5 (who renders them). Put this exact list in
both modules' READMEs and don't let it drift — this is the most common source of "works on my
machine, breaks in the demo" bugs in generative-UI projects.

---

## 10. Architecture Diagram — Info Sheet for Slide 3

Draw this as boxes + arrows (Excalidraw/draw.io), left to right:

```
[User / Fisherman]
      ↓ (natural language query, any supported language)
[Frontend: Chat UI + Generative Canvas + Map]  (Vanilla JS + Leaflet)
      ↓ POST /api/chat (SSE response)
[Backend Core Service]  (Spring Boot — Auth, Chat, Orchestration)
      ↓ POST /ai/agent/run
[AI Agent Orchestrator]  (Python, FastAPI, LangGraph)
      ├─→ Intent Agent → Planner Agent
      ├─→ Weather/Ocean Agent → reads M1 snapshot data (Open-Meteo, Open-Meteo Marine)
      ├─→ Alert Agent → reads M1 snapshot data (GDACS cyclone, simulated lightning)
      └─→ PFZ Agent + Risk/GIS calls → [Risk Engine & GIS Service]  (Spring Boot + PostGIS)
                                              ↓
                                     Deterministic risk score,
                                     nearest-PFZ, geofence check
      ↓ (evidence gathered)
[Explanation Agent] → plain-language, non-absolute recommendation
      ↓
[UI Planning Agent] → structured UI JSON (fixed component registry)
      ↓
[Backend streams UI JSON back via SSE]
      ↓
[Frontend Renderer] → Risk Card / Weather Card / Ocean Card / PFZ Map / Recommendation / Evidence Panel
```

Add a small side-box for the **Data Layer**: PostgreSQL + PostGIS (users, chat history, PFZ
points, boundaries/MPA polygons, chlorophyll snapshots).

This single diagram should cover Slide 3 entirely — ask M2/M3/M4/M5 owners to confirm their box
is accurately labeled before finalizing.
