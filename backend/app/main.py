"""The web API. The React dashboard talks to these endpoints.

Run locally:  uvicorn app.main:app --reload   (from the backend folder)
Interactive docs then live at http://localhost:8000/docs
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.predictor.model import model_metrics
from app.recovery.scenario import build_scenario
from app.recovery.simulate import format_time, run

app = FastAPI(title="Flight Recovery Engine", version="1.0.0")

# Allow the React dev server (port 5173) to call this API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class SimulationRequest(BaseModel):
    """What the dashboard sends. Field limits reject nonsense values with a clear error."""
    ground_stop_start: float = Field(14.0, ge=6, le=22, description="Hour the ground stop starts, e.g. 14.5 = 2:30 PM")
    ground_stop_end: float = Field(17.0, ge=6, le=23)
    reserve_crews: int = Field(6, ge=0, le=20)
    use_risk: bool = True


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok"}


@app.get("/api/model")
def model() -> dict:
    """How the delay model scores against the simple baseline."""
    return model_metrics()


@app.get("/api/schedule")
def schedule(ground_stop_start: float = 14.0, ground_stop_end: float = 17.0) -> list[dict]:
    """The day's flights with their predicted delay risk."""
    legs, _ = build_scenario(int(ground_stop_start * 60), int(ground_stop_end * 60), reserves=0)
    return [{"flight_no": l.flight_no, "route": f"{l.origin}-{l.dest}", "sched_dep": format_time(l.sched_dep),
             "risk": l.risk} for l in legs]


@app.post("/api/simulate")
def simulate(req: SimulationRequest) -> dict:
    """Run the ground stop through all three recovery strategies."""
    if req.ground_stop_end <= req.ground_stop_start:
        raise HTTPException(status_code=422, detail="The ground stop must end after it starts.")
    return run(int(req.ground_stop_start * 60), int(req.ground_stop_end * 60),
               req.reserve_crews, req.use_risk)
