"""
ORCA AI Agent Service (Module 4).

Run with: uvicorn main:app --reload --port 8000
Called internally by the Spring Boot Backend Core service at POST /ai/agent/run.
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
        result = run_agent(request.query, request.location.lat, request.location.lon)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
