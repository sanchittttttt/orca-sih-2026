# ORCA — Session Handoff (paste this whole file into a new chat)

## Paste-ready context block for the new LLM

```
You are continuing work on ORCA, a Smart India Hackathon 2026 project (PS 26176, ISRO) —
an agentic AI conversational marine intelligence platform for Indian fishermen and coastal
stakeholders. A prior chat session already completed significant work; this document is
the full handoff. Read it fully before suggesting anything, since several decisions below
were made deliberately after trial and error (data quality fixes, API tradeoffs, etc.) and
should not be re-litigated without reason.

Repo: github.com/sanchittttttt/orca-sih-2026 (personal repo, not an org). Team works via
feature branches + PRs into main, no branch-protection-required-reviews enforced yet
(free GitHub plan + private repo limitation, was left open, may need public repo to
enable it — flagged but not resolved).

Team: 6 people. 2 Spring Boot devs, 1 Python/AI dev, 1 frontend dev, 2 members with
limited availability handling dataset support + PPT/documentation.

Tech stack: Spring Boot (backend-core, risk-gis-service), Python + FastAPI + LangGraph
(ai-service), Vanilla JS + Leaflet (frontend), PostgreSQL + PostGIS (data layer).

Windows/PowerShell is the primary dev environment for at least one team member — adapt
shell commands accordingly, or suggest Git Bash when bash syntax is unavoidable.
```

---

## Full project state as of this handoff

### Module 1 — Dataset & Data Integration: DONE (except one deferred stretch item)

All scripts live in `data/` on branch `feature/m1-weather-fetch`, committed and pushed.

| Script | Status | Notes |
|---|---|---|
| `fetch_weather.py` | ✅ Done, committed | Reference/verification script only — proves Open-Meteo works and documents response shape. NOT part of production path; M4 will call Open-Meteo live per-query itself. |
| `fetch_marine.py` | ✅ Done, committed | Grid-fetches SST + wave data across a 2°-spaced grid over the Indian coast bounding box (8°N–22°N, 68°E–90°E). Used as PFZ input, not per-query. |
| `fetch_chlorophyll.py` | ✅ Done, committed | Uses `copernicusmarine` Python toolbox. Dataset ID: `cmems_obs-oc_glo_bgc-plankton_nrt_l3-olci-4km_P1D`. Variables: `CHL`, `CHL_gradient`. Pre-fetched/cached (not live) because the toolbox is too slow for per-query calls. |
| `compute_pfz.py` | ✅ Done, committed, validated | See methodology below — real, working, geographically validated. |
| `fetch_cyclone.py` | ✅ Done, committed | GDACS API, filtered to bounding box (0–30°N, 60–100°E). Verified working correctly (confirmed 1 global cyclone existed outside India region during testing, correctly returned 0 for India). |
| `generate_lightning_mock.py` | ✅ Done, committed | Only fully simulated dataset — no free real-time lightning API exists for India. Labeled as simulated in its own output. |
| `DATA_SOURCES.md` | ✅ Done, committed | Full transparency doc — live vs. simulated vs. computed, all methodology decisions documented. Read this before making any claims about data provenance in the PPT. |
| Boundaries/MPA (maritime boundaries + Marine Protected Areas) | ⬜ **Deferred as stretch goal** | Decided NOT to block MVP on this. Real sources identified (Marine Regions World EEZ v12 GeoJSON/GeoPackage for boundaries, Protected Planet API for MPAs) but not yet downloaded/integrated. Low demo-impact, independent of everything else — pick up only if time remains near the end. |

**Known limitation, documented but not fixed:** the chlorophyll 95th-percentile outlier cap in `compute_pfz.py` is recalculated on whichever date-filtered subset is active, rather than on the full week's distribution before filtering to one day. Can cause the cap to drift slightly. Not blocking, documented in `DATA_SOURCES.md`.

### PFZ computation methodology (important — don't re-derive from scratch)

1. Chlorophyll (Copernicus, ~4km grid) matched to nearest SST point (Open-Meteo Marine, ~2° grid) via nearest-neighbor.
2. **Critical data-quality fix**: raw chlorophyll data included values up to 290 mg/m³ near river mouths/harbors (Gulf of Kutch, Kochi backwaters, Mumbai harbor) — this is a known "turbid coastal water" satellite retrieval artifact, not real productivity. Fixed by excluding values above the 95th percentile of the real distribution (empirically ~2.74 mg/m³ in testing), derived from the data itself rather than an arbitrary guessed cutoff.
3. Score = `0.6 × normalized_chlorophyll + 0.4 × normalized_gradient`. Top 15% of scores, capped at 50 points, become the PFZ advisory list.
4. Validated: resulting top zones correctly cluster along the Kerala coast, consistent with the real, well-documented Southwest Monsoon upwelling season (this is August) — a strong signal the pipeline captures genuine signal, not noise.
5. **Framing for judges**: this is real INCOIS methodology (SST fronts + chlorophyll threshold) applied to real satellite data — NOT random/fabricated numbers. The scoring weights (0.6/0.4) and selection threshold (top 15%/50) are the team's own reasonable implementation choices since INCOIS's exact internal formula isn't public — this is disclosed honestly in `DATA_SOURCES.md`, not hidden.

### Module 6 — Documentation & PPT

- Target format confirmed: standard 6-slide SIH structure (Title → Our Solution →
  Technical Approach → Impact and Benefits → Feasibility and Viability → Prototype &
  Reference Links), based on a reviewed past-winner deck ($BLACKGOLD$, PS 1646, SIH 2024).
- Full slide-by-slide content mapping already exists in `ORCA_Module_Breakdown_and_Playbook.md`
  (Section 7) — pull directly from there rather than re-planning the structure.

### GitHub setup

- Personal repo (not an org — decided against org to reduce admin overhead for 6 people).
- Folder skeleton exists: `backend-core/`, `risk-gis-service/`, `ai-service/`, `frontend/`,
  `data/`, `docs/`, each with a placeholder README.
- `.gitignore` covers `.env`, Python/Java/Node artifacts, IDE files.
- Branch-per-task convention: `feature/m1-...`, `feature/m2-...`, etc.
- **Known unresolved issue**: branch protection on `main` requires either a public repo or
  a paid GitHub plan on a free account — this was flagged but not resolved. Team decided to
  proceed without enforced protection for now, relying on convention (branch + PR) instead
  of enforcement.

### Module 4 — AI Agent Orchestration: IN PROGRESS, this is where you pick up

**LLM provider decision**: OpenRouter (free tier), NOT Gemini, NOT a local model.
- Reasoning: needed something genuinely free with tool-calling/structured-output support.
  Gemini was proposed first (best permanent free tier for a frontier model) but the user
  explicitly wanted OpenRouter instead.
- Model string to use: `openrouter/free` — OpenRouter's own auto-router that picks a
  working free model based on request needs (tool calling, structured output, etc.).
  Chosen specifically because OpenRouter's free model catalog rotates/gets delisted
  frequently, and the auto-router avoids hardcoding a model ID that might disappear.
- **Known constraint**: free-tier limit is 50 requests/day, 20/min (rises to 1,000/day only
  after the account has ever purchased $10 of credit). This is why the user asked for a
  handoff — worried about hitting this limit mid-session. Be mindful of this when testing:
  don't loop/retry excessively, batch test calls thoughtfully.
- Setup: `openai` Python package (OpenRouter mimics OpenAI's API format), pointed at
  `base_url="https://openrouter.ai/api/v1"`, with `OPENROUTER_API_KEY` in a gitignored
  `.env` file.
- **Status of the connection test**: the user was in the middle of running the test script
  when this handoff was created. Ask them whether the test call succeeded before
  proceeding — if not, debug that first.

### IMPORTANT — orchestration framework decision changed (read this before touching LangGraph)

The original module plan (in `ORCA_Module_Breakdown_and_Playbook.md`) says LangGraph.
**This was deliberately overridden in a later decision — do not use LangGraph, and do not
use any no-code agent builder (Flowise, LangFlow, n8n) either.**

**Clarification in case this raises doubt later: dropping LangGraph does NOT mean this
project stops being "agentic."** Being agentic is a behavior (reasoning about what to do
next, deciding which tools/data are needed, specialized components handing off work to
each other) — not a specific library. LangGraph is just one way to wire that up; it isn't
what makes something an agent. The four functions below (`classify_intent`,
`decide_what_data_is_needed`, `explain_evidence`, `build_ui`) are still four genuine
specialized agents collaborating in sequence — which is exactly what the project's own
name describes ("Collaborative Agents"). This is accurately described in the pitch deck as
"a multi-agent architecture with specialized reasoning agents for intent classification,
data planning, explanation, and adaptive UI generation" — true regardless of whether
LangGraph appears in the tech stack. What WOULD have made it non-agentic is a single
hardcoded if/else block with no reasoning steps — that is not what's being built here.

Reasoning: the actual pipeline is 4-5 steps that run in a straight line (classify → plan →
fetch data → explain → build UI) — not the branching/looping/multi-node state management
LangGraph exists to solve. Using it adds a learning curve and a new failure surface for no
real benefit at this scale, and is riskier to have break live during a demo. No-code tools
are worse specifically because this project needs precise Pydantic schema validation (the
UI JSON contract with the frontend) and custom calls into M1's files and M3's REST
endpoints — both awkward inside a visual builder, and both add an extra service that can
independently fail on presentation day.

**Use plain Python functions instead**, one orchestrator calling each step in order:

```python
def run_agent(query: str, location: dict) -> dict:
    intent = classify_intent(query)              # 1 LLM call
    plan = decide_what_data_is_needed(intent)     # 1 LLM call, or even just if/else logic
    evidence = gather_data(plan, location)        # calls M1 functions/files, no LLM needed
    explanation = explain_evidence(evidence)      # 1 LLM call
    ui_json = build_ui(evidence, explanation)     # 1 LLM call, validated against Pydantic schema
    return {"ui_json": ui_json, "explanation_text": explanation}
```

This is still a genuine multi-step reasoning pipeline with tool use — it satisfies
"agentic AI" for the problem statement and the pitch deck just fine. It's just not wrapped
in a framework that isn't needed here. Easier to debug live, easier to read, nothing extra
to install beyond OpenRouter + the `openai` package already set up.

### What to build next in M4 (in order — updated, no LangGraph)

1. ~~Provider setup~~ (in progress, confirm the OpenRouter test call worked first)
2. **Pydantic schema for `ui_json`** — do this next, before any agent logic. This is the
   hard contract with the frontend (M5) and must not drift. Fixed component types the
   schema must support: `risk-card`, `weather-card`, `ocean-card`, `pfz-card`,
   `marine-map`, `alert-card`, `recommendation-card`, `evidence-panel`. Structure:
   `{"title": str, "components": [{"type": str, "data": dict}]}`
3. **Tool wrappers** — thin functions around: live Open-Meteo weather call, live
   Open-Meteo Marine call, reading `pfz_points.json` (M1's precomputed output), a
   temporary local risk-score function using the fixed formula below (until M3's real
   service exists to call instead).
4. **`classify_intent(query)`** — one function, one LLM call, classify query intent and
   extract location/time/language.
5. **`decide_what_data_is_needed(intent)`** — decide which of weather/ocean/PFZ/alerts/
   geofencing are needed. Can be plain if/else logic instead of an LLM call if the intent
   categories are simple enough — don't reach for an LLM call by default here.
6. **`explain_evidence(evidence)`** — one LLM call, turn retrieved evidence into plain,
   NEVER-absolute language (e.g. "assessed as MODERATE RISK", never "yes it's safe").
7. **`build_ui(evidence, explanation)`** — one LLM call, select components from the fixed
   registry, populate data, validate against the Pydantic schema before returning. Retry
   once on validation failure; fall back to a generic RecommendationCard + EvidencePanel
   if it fails twice.
8. Write the single `run_agent()` orchestrator function chaining steps 4-7 in order (see
   code block above) — no framework needed.
9. Expose `POST /ai/agent/run` via FastAPI, matching the contract in
   `ORCA_Module_Breakdown_and_Playbook.md` Section 5, calling `run_agent()` internally.
10. Test end-to-end with a real query against real M1 data (e.g. PFZ near Ratnagiri).

### Before your AI-agent teammate starts: branch setup

The M1 work (all of `data/`) currently lives on `feature/m1-weather-fetch` and has **not
yet been merged into `main`**. Before anyone starts M4, do this or they'll be missing
`pfz_points.json`, `DATA_SOURCES.md`, and every other M1 output:

1. Open a Pull Request on GitHub: `feature/m1-weather-fetch` → `main`, merge it.
2. Whoever is building M4 runs:
   ```bash
   git checkout main
   git pull
   git checkout -b feature/m4-ai-service
   ```
3. Confirm they can see the `data/` folder with all the M1 scripts/outputs before writing
   any AI-service code — M4 depends on reading `pfz_points.json` and reusing the same
   Open-Meteo call pattern from `fetch_weather.py`.

### Fixed risk formula (deterministic — the LLM must NEVER invent this, only call it)

```
score = windScore*0.25 + waveScore*0.25 + rainScore*0.15 + lightningScore*0.15 + cycloneScore*0.20
0–30 LOW · 31–60 MODERATE · 61–80 HIGH · 81–100 EXTREME
```
This formula is owned by M3 (Spring Boot Risk Engine) long-term, but until that service
exists, M4 needs a local Python equivalent to keep developing against.

### Safety principle to maintain throughout M4

The LLM must never invent a risk score, PFZ coordinate, or weather number. It only:
retrieves real data via tool calls, explains it in plain language, and selects/populates
UI components. This was emphasized repeatedly across the whole project and should not be
compromised for convenience while building agents.

---

## Immediate next action for whoever picks this up

Ask the user: "Did the OpenRouter test call succeed?" If yes, move straight to writing the
Pydantic `ui_json` schema. If no, paste the error and debug the OpenRouter connection first
before building anything on top of it.
