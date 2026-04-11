"""
main.py — FastAPI server for InfraAgent-Env v2.0
Endpoints: POST /reset  POST /step  GET /state  GET /health  GET /tasks  GET /
"""
from __future__ import annotations
from contextlib import asynccontextmanager
from typing import Optional
import os

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse

from env.infra_env import InfraEnv
from env.schemas import InfraAction, StepResult, ResetResult, InfraState

_env: Optional[InfraEnv] = None
DEFAULT_TASK = os.getenv("TASK_ID", "task1_incident_recovery")


@asynccontextmanager
async def lifespan(app: FastAPI):
    global _env
    _env = InfraEnv(task_id=DEFAULT_TASK)
    _env.reset()
    yield
    _env = None


app = FastAPI(
    title="InfraAgent-Env",
    description="Microservice-aware OpenEnv RL environment for autonomous SRE agents.",
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_env() -> InfraEnv:
    if _env is None:
        raise HTTPException(status_code=500, detail="Environment not initialized.")
    return _env


# ── Dashboard ─────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the live dashboard UI."""
    try:
        with open("dashboard/dashboard.html", encoding="utf-8") as f:
            return HTMLResponse(content=f.read())
    except FileNotFoundError:
        return HTMLResponse(
            content="<h2 style='font-family:monospace;color:#f87171;padding:40px'>"
                    "dashboard/dashboard.html not found</h2>",
            status_code=404,
        )


# ── OpenEnv required endpoints ────────────────────────────────────────────────

@app.post("/reset", response_model=ResetResult)
async def reset(
    task_id: Optional[str] = Query(default=None),
    seed:    Optional[int]  = Query(default=42),
):
    """
    Reset the environment to initial state.
    Query params: task_id, seed
    Returns: initial observation.
    """
    global _env
    task = task_id or DEFAULT_TASK
    try:
        _env = InfraEnv(task_id=task, seed=seed)
        return _env.reset()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/step", response_model=StepResult)
async def step(action: InfraAction):
    """
    Execute one action in the environment.
    Returns: observation, reward, done, info.
    """
    env = get_env()
    try:
        return env.step(action)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/state", response_model=InfraState)
async def state():
    """Return full internal environment state."""
    return get_env().state()


# ── Utility endpoints ─────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health check — used by Docker HEALTHCHECK and inference.py polling."""
    return {"status": "ok", "version": "2.0.0"}


@app.get("/tasks")
async def list_tasks():
    """List available tasks with metadata."""
    return {
        "tasks": [
            {
                "id":          "task1_incident_recovery",
                "difficulty":  "easy",
                "max_steps":   100,
                "description": "Sudden traffic spike — diagnose bottleneck and restore SLA.",
            },
            {
                "id":          "task2_predictive_scaling",
                "difficulty":  "medium",
                "max_steps":   150,
                "description": "Pre-scale services before flash traffic spikes arrive.",
            },
            {
                "id":          "task3_root_cause",
                "difficulty":  "hard",
                "max_steps":   200,
                "description": "Silent DB fault causes cascading failures — diagnose and fix.",
            },
        ]
    }
