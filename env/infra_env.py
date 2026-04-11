"""
infra_env.py — Main OpenEnv environment class v2
Implements reset() / step() / state() — OpenEnv spec compliant.
Microservice-aware with cascading failures and queue simulation.
"""

import os
import yaml
from typing import Optional, List
from env.schemas import (
    InfraAction, InfraObservation, InfraReward, InfraState,
    StepResult, ResetResult, ServiceMetrics, ActionType,
)
from env.simulator import MicroserviceSimulator, TrafficSimulator
from env.incident_engine import IncidentEngine
from utils.reward_utils import RewardCalculator
from utils.infra_utils import build_summary, get_alert

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "../config/env_config.yaml")

TASK_MAX_STEPS = {
    "task1_incident_recovery":  100,
    "task2_predictive_scaling": 150,
    "task3_root_cause":         200,
}

SLA_MS = 200.0


def load_config() -> dict:
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


class InfraEnv:
    """
    InfraAgent-Env v2: Microservice-aware OpenEnv environment.

    Tasks:
        task1_incident_recovery  — system already degraded, recover it
        task2_predictive_scaling — ramp + surge, pre-scale before it hits
        task3_root_cause         — cascading failures, diagnose root cause
    """

    def __init__(self, task_id: str = "task1_incident_recovery", seed: int = 42):
        self.task_id = task_id
        self.seed = seed
        self.config = load_config()
        self.max_steps = TASK_MAX_STEPS.get(task_id, 100)

        self.traffic_sim  = TrafficSimulator(task_id=task_id, seed=seed)
        self.ms_sim       = MicroserviceSimulator(seed=seed)
        self.incident_eng = IncidentEngine(task_id=task_id, seed=seed)
        self.reward_calc  = RewardCalculator()

        self._reset_state()

    # ------------------------------------------------------------------
    # OpenEnv interface
    # ------------------------------------------------------------------

    def reset(self) -> ResetResult:
        self._reset_state()
        self.traffic_sim.reset()
        self.ms_sim.reset()
        self.incident_eng.reset()
        obs = self._build_observation(
            sim_result=self._get_initial_sim(),
            rps=self.traffic_sim.get_rps(0),
        )
        return ResetResult(observation=obs, info={"task_id": self.task_id})

    def step(self, action: InfraAction) -> StepResult:
        if self._done:
            raise RuntimeError("Episode done. Call reset() first.")

        self._time_step += 1
        action_type = (action.action_type or "do_nothing")
        service     = (action.service or "api")
        value       = (action.value or 1)

        # Track stability
        last = self._last_action
        self._last_action = action_type
        if action_type == "do_nothing" or action_type == last:
            self._stable_steps += 1
        else:
            self._stable_steps = 0

        # Maybe inject / cascade incident
        self.incident_eng.maybe_inject(self._time_step)
        self.incident_eng.maybe_cascade(self._time_step)

        # Check if action is a remediation attempt
        fix_attempted = False
        fix_success   = False
        fix_message   = None

        REMEDIATION_ACTIONS = {
            "restart_service", "clear_queue", "adjust_cache",
        }
        SCALE_ACTIONS = {"scale_service"}

        if action_type in REMEDIATION_ACTIONS or (
            action_type == "scale_service" and self.incident_eng.active
        ):
            fix_attempted = True
            fix_success, fix_message = self.incident_eng.attempt_remediation(
                action_type, service
            )
            if fix_success:
                self.incident_eng.resolved_step = self._time_step

        # Simulate one step
        rps = self.traffic_sim.get_rps(self._time_step)
        sim_result = self.ms_sim.step(
            rps=rps,
            action_type=action_type,
            action_service=service,
            action_value=value,
            incident_type=self.incident_eng.get_cascade_type() or "none",
            incident_service=self.incident_eng.get_cascade_service() or "",
        )

        # Apply incident latency multiplier
        multiplier = self.incident_eng.get_latency_multiplier()
        sim_result["avg_latency_ms"] = round(
            min(9999, sim_result["avg_latency_ms"] * multiplier), 1
        )
        sim_result["p99_latency_ms"] = round(
            min(9999, sim_result["p99_latency_ms"] * multiplier), 1
        )

        latency = sim_result["avg_latency_ms"]
        self._total_cost += sim_result["cost_per_step"]

        if latency > SLA_MS:
            self._sla_breaches += 1

        # Reward
        reward_detail = self.reward_calc.compute(
            latency=latency,
            p99_latency=sim_result["p99_latency_ms"],
            sla_ms=SLA_MS,
            total_replicas=sum(self.ms_sim.replicas.values()),
            stable_steps=self._stable_steps,
            incident_active=self.incident_eng.active,
            fix_attempted=fix_attempted,
            fix_success=fix_success,
            wrong_attempts=self.incident_eng.wrong_attempts,
            logs_read=self.incident_eng.logs_read,
            task_id=self.task_id,
        )
        self._episode_rewards.append(reward_detail.total)

        # Done?
        self._done = self._time_step >= self.max_steps
        obs = self._build_observation(sim_result=sim_result, rps=rps)

        info = {
            "task_id": self.task_id,
            "time_step": self._time_step,
            "sla_breaches": self._sla_breaches,
            "total_cost": round(self._total_cost, 4),
            "incident_active": self.incident_eng.active,
            "cascade_level": self.incident_eng.cascade_level,

            # ADD THESE
            "incident_resolved": not self.incident_eng.active,
            "correct_remediation": fix_success,
            "wrong_attempts": self.incident_eng.wrong_attempts,
        }
        if fix_message:
            info["fix_message"] = fix_message

        return StepResult(
            observation=obs,
            reward=reward_detail.total,
            reward_detail=reward_detail,
            done=self._done,
            info=info,
        )

    def state(self) -> InfraState:
        rps = self.traffic_sim.get_rps(self._time_step)
        sim = self.ms_sim.step(
            rps=rps,
            action_type="do_nothing",
            action_service="api",
            action_value=0,
            incident_type="none",
            incident_service="",
        )
        services = self._build_service_metrics(sim["service_metrics"])
        return InfraState(
            task_id=self.task_id,
            time_step=self._time_step,
            services=services,
            total_rps=round(rps, 1),
            avg_latency_ms=sim["avg_latency_ms"],
            queue_size=sim["queue_size"],
            db_connections=sim["db_connections"],
            cache_hit_rate=sim["cache_hit_rate"],
            total_cost=round(self._total_cost, 4),
            sla_breaches=self._sla_breaches,
            episode_rewards=self._episode_rewards,
            done=self._done,
            incident_active=self.incident_eng.active,
            incident_type=self.incident_eng.incident_type,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _reset_state(self):
        self._time_step   = 0
        self._total_cost  = 0.0
        self._sla_breaches = 0
        self._episode_rewards: List[float] = []
        self._done        = False
        self._last_action = None
        self._stable_steps = 0

    def _get_initial_sim(self) -> dict:
        return {
            "service_metrics": {
                s: {"cpu": 10.0, "latency_ms": 20.0, "queue_size": 0,
                    "error_rate": 0.0, "status": "healthy", "replicas": self.ms_sim.replicas[s]}
                for s in ["api", "auth", "db", "cache", "queue"]
            },
            "avg_latency_ms": 30.0,
            "p99_latency_ms": 45.0,
            "avg_cpu": 10.0,
            "queue_size": 0,
            "db_connections": 5,
            "cache_hit_rate": 0.85,
            "latency_history": [30.0] * 10,
            "cost_per_step": sum(self.ms_sim.replicas.values()) * 0.05,
        }

    def _build_service_metrics(self, svc_dict: dict) -> List[ServiceMetrics]:
        out = []
        for name, m in svc_dict.items():
            out.append(ServiceMetrics(
                name=name,
                replicas=m.get("replicas", 1),
                cpu_percent=m.get("cpu", 0.0),
                latency_ms=m.get("latency_ms", 0.0),
                queue_size=m.get("queue_size", 0),
                error_rate=m.get("error_rate", 0.0),
                status=m.get("status", "healthy"),
            ))
        return out

    def _build_observation(self, sim_result: dict, rps: float) -> InfraObservation:
        services = self._build_service_metrics(sim_result["service_metrics"])
        latency  = sim_result["avg_latency_ms"]
        trend    = self.traffic_sim.get_traffic_trend(self._time_step)
        spike_w  = self.traffic_sim.get_spike_warning(self._time_step)
        alert_level, alert_msg = get_alert(
            latency=latency,
            sla_ms=SLA_MS,
            incident_active=self.incident_eng.active,
            incident_type=self.incident_eng.incident_type,
            queue_size=sim_result["queue_size"],
            db_connections=sim_result["db_connections"],
        )
        summary = build_summary(
            time_step=self._time_step,
            task_id=self.task_id,
            rps=rps,
            latency=latency,
            p99=sim_result["p99_latency_ms"],
            sla_ms=SLA_MS,
            services=services,
            queue_size=sim_result["queue_size"],
            db_connections=sim_result["db_connections"],
            cache_hit_rate=sim_result["cache_hit_rate"],
            incident_active=self.incident_eng.active,
            incident_type=self.incident_eng.incident_type,
            cascade_level=self.incident_eng.cascade_level,
            spike_warning=spike_w,
            alert_level=alert_level,
            alert_msg=alert_msg,
        )
        return InfraObservation(
            time_step=self._time_step,
            total_rps=round(rps, 1),
            avg_latency_ms=latency,
            p99_latency_ms=sim_result["p99_latency_ms"],
            sla_breach=(latency > SLA_MS),
            cost_per_step=sim_result["cost_per_step"],
            services=services,
            queue_size=sim_result["queue_size"],
            db_connections=sim_result["db_connections"],
            cache_hit_rate=sim_result["cache_hit_rate"],
            latency_history=sim_result.get("latency_history", [latency] * 10),
            alert_level=alert_level,
            alert_message=alert_msg,
            traffic_trend=trend,
            spike_warning=spike_w,
            summary=summary,
        )
