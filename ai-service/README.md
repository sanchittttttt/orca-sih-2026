# ORCA AI Agent Service (Module 4) — v2, simplified

Rebuilt using only `requests` for OpenRouter — no `openai` package, no
LangChain, no LangGraph. This was a deliberate fix after the first version's
`openai` package caused environment/dependency issues.

## Only 5 dependencies

`fastapi`, `uvicorn`, `requests`, `python-dotenv`, `pydantic` — nothing else.

## Setup

```bash
cd ai-service
python -m venv venv
venv\Scripts\activate        # Windows PowerShell
# or: source venv/bin/activate

pip install -r requirements.txt
copy .env.example .env       # Windows: copy, Mac/Linux: cp
```
Then open `.env` and paste your real OpenRouter key (get one free, no card,
at https://openrouter.ai/keys).

Make sure `../data/pfz_points.json` and `../data/lightning_alerts.json` exist
(from Module 1's scripts) — the service reads these directly, no duplication.
Small samples are included in `data/` here so it runs out of the box.

## Run

```bash
uvicorn main:app --reload --port 8000
```

## Test

```bash
curl http://localhost:8000/health
```
```bash
curl -X POST http://localhost:8000/ai/agent/run -H "Content-Type: application/json" -d "{\"query\": \"Is it safe to go fishing tomorrow?\", \"location\": {\"lat\": 16.99, \"lon\": 73.31}}"
```
(That's the Windows-quoting-friendly version — the escaped quotes matter in PowerShell.)

## Architecture notes

- No LangGraph — plain function pipeline (`classify_intent` → `decide_what_data_is_needed`
  → `gather_data` → `explain_evidence` → `build_ui`), chained in `orchestrator.py`.
- No `openai` SDK — `llm_client.py` calls OpenRouter's REST API directly with `requests`.
- Model used: `openrouter/free` (OpenRouter's auto-router — expect to see different
  underlying free models across calls, that's normal — you already confirmed this works).
- Safety rule: the LLM only explains/selects/arranges real data from `tools.py` — it
  never invents a risk score, weather number, or PFZ coordinate.
