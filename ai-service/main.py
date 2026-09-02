"""
ORCA AI Agent Service (Module 4).
Run with: uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI, HTTPException

from orchestrator import run_agent
from schemas import AgentRequest, AgentResponse

app = FastAPI(title="ORCA AI Agent Service")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/ai/agent/run", response_model=AgentResponse)
def agent_run(request: AgentRequest):
    try:
        history = [h.model_dump() for h in request.history] if request.history else None
        result = run_agent(
            request.query,
            request.location.lat,
            request.location.lon,
            history=history,
        )
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))