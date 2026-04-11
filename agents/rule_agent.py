"""agents/rule_agent.py — Rule-based SRE agent. Mid-tier baseline."""
from env.schemas import InfraAction, ActionType


class RuleAgent:
    """Mimics a simple on-call SRE with fixed runbooks."""

    SLA_MS = 200
    SCALE_COOLDOWN = 5

    def __init__(self):
        self._step = 0
        self._last_scale = -99

    def act(self, obs: dict) -> InfraAction:
        self._step += 1
        latency = obs.get("avg_latency_ms", 100)
        alert = obs.get("alert_level", "none")
        incident = obs.get("alert_message", "")
        services = {s["name"]: s for s in obs.get("services", [])}
        queue = obs.get("queue_size", 0)
        db_conn = obs.get("db_connections", 0)
        cooldown_ok = (self._step - self._last_scale) >= self.SCALE_COOLDOWN

        # Handle incident alerts
        if alert == "critical":
            if "db_overload" in incident or db_conn > 150:
                self._last_scale = self._step
                return InfraAction(action_type=ActionType.SCALE_SERVICE, service="db", value=2)
            if "queue_flood" in incident or queue > 3000:
                return InfraAction(action_type=ActionType.CLEAR_QUEUE, service="queue")
            if "cache_invalidation" in incident:
                return InfraAction(action_type=ActionType.ADJUST_CACHE, service="cache")
            if "service_crash" in incident or "auth_degraded" in incident:
                svc = "api" if "service_crash" in incident else "auth"
                return InfraAction(action_type=ActionType.RESTART_SERVICE, service=svc)

        # Scale API if latency high
        api = services.get("api", {})
        if latency > self.SLA_MS and api.get("replicas", 1) < 10 and cooldown_ok:
            self._last_scale = self._step
            return InfraAction(action_type=ActionType.SCALE_SERVICE, service="api", value=2)

        # Scale down if latency very low
        if latency < 80 and api.get("replicas", 1) > 2 and cooldown_ok:
            self._last_scale = self._step
            return InfraAction(action_type=ActionType.SCALE_SERVICE, service="api", value=-1)

        return InfraAction(action_type=ActionType.DO_NOTHING)
