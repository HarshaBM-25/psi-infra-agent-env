"""
main.py — FastAPI server. OpenEnv HTTP endpoints.
POST /reset  POST /step  GET /state  GET /health
"""

from contextlib import asynccontextmanager
from typing import Optional
import os

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

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
    title="InfraAgent-Env v2",
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


@app.post("/reset", response_model=ResetResult)
async def reset(
    task_id: Optional[str] = Query(default=None),
    seed: Optional[int] = Query(default=42),
):
    global _env
    task = task_id or DEFAULT_TASK
    try:
        _env = InfraEnv(task_id=task, seed=seed)
        return _env.reset()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/step", response_model=StepResult)
async def step(action: InfraAction):
    env = get_env()
    try:
        return env.step(action)
    except RuntimeError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/state", response_model=InfraState)
async def state():
    return get_env().state()


@app.get("/health")
async def health():
    return {"status": "ok", "version": "2.0.0"}


@app.get("/tasks")
async def tasks():
    return {"tasks": [
        {"id": "task1_incident_recovery",  "difficulty": "easy",   "max_steps": 100},
        {"id": "task2_predictive_scaling", "difficulty": "medium",  "max_steps": 150},
        {"id": "task3_root_cause",         "difficulty": "hard",    "max_steps": 200},
    ]}


@app.get("/")
async def root():
    return {
        "name": "InfraAgent-Env v2",
        "version": "2.0.0",
        "endpoints": ["/reset", "/step", "/state", "/health", "/tasks", "/docs"],
    }
