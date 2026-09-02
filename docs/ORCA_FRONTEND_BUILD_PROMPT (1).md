# Build Prompt — ORCA Frontend (Module 5)

## Context

ORCA is a Smart India Hackathon project (PS 26176, ISRO) — an agentic AI conversational
marine intelligence platform. This is the frontend: a chat interface plus a "generative
UI" canvas that renders different components depending on what the backend decides is
relevant to each query, plus a map.

## Stack

Vanilla HTML, CSS, JavaScript. No React, no build tooling, no framework. Leaflet
(via CDN) for the map.

## What's already working, so you're building against something real, not a guess

The backend chain (frontend's contract) has already been tested end-to-end twice with
real live data and a real LLM. This isn't a theoretical spec — it's what's actually
coming back from the server right now.

## The API you call

`POST http://localhost:8081/api/chat`

Request body:
```json
{
  "query": "Is it safe to go fishing tomorrow?",
  "location": {"lat": 16.99, "lon": 73.31}
}
```

**Important, current limitation:** this is currently a plain synchronous request —
you send it and wait for the full response, there is no streaming/SSE yet. The response
can take 20-60+ seconds because it involves multiple LLM calls on a free-tier API.
**Show a loading state that makes clear something is happening** (a spinner with
rotating text like "Checking weather conditions..." is fine even without real progress
events — it doesn't need to reflect real backend state yet, just avoid a static blank
screen for up to a minute). SSE streaming with real progressive status may be added later
as an upgrade — build against the plain synchronous response for now, don't build SSE
handling yet.

Response body:
```json
{
  "ui_json": {
    "title": "string",
    "components": [
      {"type": "string", "data": {...}}
    ]
  },
  "explanation_text": "string"
}
```

## The component registry — LOCKED field names, do not deviate

`ui_json.components[].type` will always be one of these 8 exact strings, and each one's
`data` object will always use exactly these field names (the backend is being kept
strictly consistent with this — if you ever see a different field name, that's a bug on
the backend side, flag it, don't silently adapt your frontend to match a one-off case):

### `risk-card`
```json
{"score": 28.5, "level": "LOW"}
```
`level` is always one of: `"LOW"`, `"MODERATE"`, `"HIGH"`, `"EXTREME"`. Suggest a
color-coded badge (e.g. green/yellow/orange/red) rather than just plain text — this is
the single most important number on the screen.

### `weather-card`
```json
{"temperature_c": 27.3, "windspeed_kmh": 22.6, "winddirection_deg": 286, "precipitation_probability": 90}
```
All numbers, no units baked into the values — append units yourself in the UI (°C,
km/h, °, %).

### `ocean-card`
```json
{"wave_height_m": 1.68, "wave_direction_deg": 264, "wave_period_s": 7.0, "sea_surface_temperature_c": 28.5}
```
Same rule — plain numbers, add units in your rendering.

### `pfz-card`
```json
{"zones": [{"latitude": 9.19, "longitude": 76.35, "chlorophyll": 2.71, "pfz_score": 0.71}]}
```
An array — could be empty, 1 item, or several. Render as a short list, and ideally also
drop markers on the map (see `marine-map` below) if a map is already showing.

### `alert-card`
```json
{
  "cyclone_alerts": [{"event_name": "string", "alert_level": "string", "latitude": 0, "longitude": 0}],
  "lightning_alerts": [{"region": "string", "lightning_alert": "none|moderate|severe"}]
}
```
Both arrays can be empty — an empty `cyclone_alerts` array means "no active cyclones,"
which is a genuinely reassuring result worth displaying positively, not just hiding the
card.

### `marine-map`
```json
{"markers": [{"latitude": 9.19, "longitude": 76.35, "label": "string"}]}
```
Render with Leaflet. Markers array could be empty.

### `recommendation-card`
```json
{"text": "string"}
```
This is often the fallback component when something else fails upstream — always handle
it, it may appear alone without other cards.

### `evidence-panel`
```json
{}
```
Deliberately unstructured — this is a "raw data" / "show your work" panel. Render it as
a collapsed/expandable JSON dump or simple key-value list rather than trying to build
specific UI for it; its shape can vary.

## Rendering rules

- Build one render function per component type in a `components.js` file — a simple
  lookup object mapping `type` string → render function is enough, no need for anything
  fancier.
- **If a component's `type` isn't in your registry, skip it silently** — log a console
  warning, but don't crash the whole render. The backend/AI service should only ever send
  these 8 types, but defensive handling costs nothing and prevents one bad component from
  taking down the whole screen.
- Clear the canvas and re-render fully on each new response — don't try to diff/patch
  the previous render, not worth the complexity here.
- `explanation_text` should be shown prominently near the top, in plain readable prose —
  it's the actual answer in human language; the components are supporting detail.

## What NOT to build yet

- No SSE/streaming handling — plain request/response only, for now.
- No auth UI (login/register forms) — not blocking, can be added once the backend's auth
  endpoints exist; for now just call `/api/chat` directly without a token.
- No offline/PWA support — not a requirement for a hackathon demo.

## Testing without a backend running

If you want to build UI before the backend/AI service are both up and running
simultaneously, hardcode a sample response matching the exact shapes above and render
directly from that, then swap in the real `fetch()` call once ready. This lets you build
independently in parallel with backend work.
