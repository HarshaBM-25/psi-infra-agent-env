"""
schemas.py — Typed Pydantic models for InfraAgent-Env v2
OpenEnv spec compliant. Microservice-aware observation and action spaces.
"""

from enum import Enum
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ActionType(str, Enum):
    SCALE_SERVICE    = "scale_service"
    RESTART_SERVICE  = "restart_service"
    REROUTE_TRAFFIC  = "reroute_traffic"
    CLEAR_QUEUE      = "clear_queue"
    ADJUST_CACHE     = "adjust_cache"
    DO_NOTHING       = "do_nothing"


class ServiceStatus(str, Enum):
    HEALTHY      = "healthy"
    DEGRADED     = "degraded"
    OVERLOADED   = "overloaded"
    DOWN         = "down"


class AlertLevel(str, Enum):
    NONE     = "none"
    WARNING  = "warning"
    CRITICAL = "critical"


# ---------------------------------------------------------------------------
# Action
# ---------------------------------------------------------------------------

class InfraAction(BaseModel):
    """Action the agent takes each step."""
    action_type: ActionType = Field(..., description="Type of infrastructure action")
    service: Optional[str] = Field(None, description="Target service name: api, auth, db, cache, queue")
    value: Optional[int] = Field(None, description="Numeric value (e.g. replica count)")

    class Config:
        use_enum_values = True


# ---------------------------------------------------------------------------
# Per-service metrics
# ---------------------------------------------------------------------------

class ServiceMetrics(BaseModel):
    name: str
    replicas: int
    cpu_percent: float
    latency_ms: float
    queue_size: int
    error_rate: float
    status: str


# ---------------------------------------------------------------------------
# Observation
# ---------------------------------------------------------------------------

class InfraObservation(BaseModel):
    """What the agent observes at each step — microservice-aware."""

    # Global metrics
    time_step: int
    total_rps: float
    avg_latency_ms: float
    p99_latency_ms: float
    sla_breach: bool
    cost_per_step: float

    # Per-service snapshots
    services: List[ServiceMetrics]

    # Queue and DB pressure
    queue_size: int
    db_connections: int
    cache_hit_rate: float

    # Latency history (short time series for trend detection)
    latency_history: List[float]

    # Alert signals
    alert_level: str
    alert_message: str

    # Traffic context
    traffic_trend: str
    spike_warning: Optional[str]

    # Human-readable summary for LLM
    summary: str

    class Config:
        use_enum_values = True


# ---------------------------------------------------------------------------
# Reward
# ---------------------------------------------------------------------------

class InfraReward(BaseModel):
    """Detailed reward breakdown — always partial, never binary."""
    total: float
    latency_score: float
    sla_score: float
    cost_score: float
    stability_score: float
    recovery_score: float
    penalty: float


# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

class InfraState(BaseModel):
    """Full internal environment state."""
    task_id: str
    time_step: int
    services: List[ServiceMetrics]
    total_rps: float
    avg_latency_ms: float
    queue_size: int
    db_connections: int
    cache_hit_rate: float
    total_cost: float
    sla_breaches: int
    episode_rewards: List[float]
    done: bool
    incident_active: bool
    incident_type: Optional[str]


# ---------------------------------------------------------------------------
# Step / Reset results
# ---------------------------------------------------------------------------

class StepResult(BaseModel):
    observation: InfraObservation
    reward: float
    reward_detail: InfraReward
    done: bool
    info: Dict = Field(default_factory=dict)


class ResetResult(BaseModel):
    observation: InfraObservation
    info: Dict = Field(default_factory=dict)
