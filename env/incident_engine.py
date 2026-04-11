"""
incident_engine.py — Incident injection and cascading failure simulation.
Models realistic failure chains:
  traffic spike → queue buildup → db overload → API latency increase
"""

import random
from typing import Optional, Tuple


# Incident type → correct remediation action
CORRECT_REMEDIATION = {
    "service_crash":      ("restart_service", "api"),
    "db_overload":        ("scale_service",   "db"),
    "queue_flood":        ("clear_queue",     "queue"),
    "cache_invalidation": ("adjust_cache",    "cache"),
    "auth_degraded":      ("restart_service", "auth"),
}

INCIDENT_DESCRIPTIONS = {
    "service_crash": (
        "CRITICAL: API service pod crashed. OOMKilled at 512Mi limit.\n"
        "Error logs: kernel OOM killer triggered. Service unreachable.\n"
        "Impact: All requests failing. Immediate restart required."
    ),
    "db_overload": (
        "WARNING: Database connection pool saturated (198/200 connections).\n"
        "Slow query log: 47 queries > 2s. Table locks detected.\n"
        "Impact: Auth and API latency spiking due to DB wait time."
    ),
    "queue_flood": (
        "CRITICAL: Message queue depth at 4,823 (limit: 5,000).\n"
        "Consumer lag: 2m 34s behind producers. Dead letter queue growing.\n"
        "Impact: Requests queuing up. Backpressure reaching API layer."
    ),
    "cache_invalidation": (
        "WARNING: Cache hit rate dropped from 85% to 23%. Mass invalidation event.\n"
        "DB read throughput increased 4x. Connection pool pressure rising.\n"
        "Impact: Cascading DB load causing latency increases across all services."
    ),
    "auth_degraded": (
        "WARNING: Auth service degraded. Token validation latency: 850ms (normal: 12ms).\n"
        "JWT verification failures: 12% of requests. Certificate rotation in progress.\n"
        "Impact: All authenticated requests delayed. User-facing latency elevated."
    ),
}

NOISE_PREFIX = [
    "INFO: healthcheck /health 200 OK 2ms\n",
    "DEBUG: connection pool size: 10, idle: 3\n",
    "INFO: metrics scrape completed successfully\n",
]


class IncidentEngine:
    """
    Manages incident injection, cascading effects, and remediation tracking.
    Used across all 3 tasks with different injection strategies.
    """

    def __init__(self, task_id: str, seed: int = 42):
        self.task_id = task_id
        self.seed = seed
        self._rng = random.Random(seed)
        self.reset()

    def reset(self):
        self._rng = random.Random(self.seed)
        self.active: bool = False
        self.incident_type: Optional[str] = None
        self.incident_service: Optional[str] = None
        self.injected_step: Optional[int] = None
        self.resolved_step: Optional[int] = None
        self.logs_read: bool = False
        self.correct_remediation: bool = False
        self.wrong_attempts: int = 0
        self.resolved: bool = False

        # Cascading failure state
        self.cascade_level: int = 0    # 0=none, 1=degraded, 2=failing, 3=critical
        self.affected_services: list = []

    def maybe_inject(self, time_step: int) -> bool:
        """
        Inject incident based on task strategy.
        Task 1: pre-injected at step 0 (system already degraded)
        Task 2: inject at step 50 (during ramp)
        Task 3: inject at step 35 + cascade at step 60
        """
        if self.active or self.resolved:
            return False

        should_inject = False
        if self.task_id == "task1_incident_recovery" and time_step == 1:
            should_inject = True
        elif self.task_id == "task2_predictive_scaling" and time_step == 50:
            should_inject = True
        elif self.task_id == "task3_root_cause" and time_step == 35:
            should_inject = True

        if should_inject:
            incident_pool = list(CORRECT_REMEDIATION.keys())
            self.incident_type = self._rng.choice(incident_pool)
            correct_action, correct_service = CORRECT_REMEDIATION[self.incident_type]
            self.incident_service = correct_service
            self.active = True
            self.injected_step = time_step
            self.cascade_level = 1
            self.affected_services = [correct_service]
            return True

        return False

    def maybe_cascade(self, time_step: int) -> bool:
        """Task 3: inject a second cascading failure at step 60."""
        if self.task_id != "task3_root_cause":
            return False
        if time_step == 60 and self.active:
            self.cascade_level = min(3, self.cascade_level + 1)
            # Add DB overload on top of existing incident
            if "db" not in self.affected_services:
                self.affected_services.append("db")
            return True
        return False

    def get_logs(self) -> str:
        """Return logs when agent calls read_logs / investigate."""
        if not self.active or not self.incident_type:
            return "No active incidents. All services nominal."
        self.logs_read = True
        noise = "".join(self._rng.choices(NOISE_PREFIX, k=2))
        return noise + INCIDENT_DESCRIPTIONS.get(self.incident_type, "Unknown incident.")

    def attempt_remediation(self, action_type: str, service: str) -> Tuple[bool, str]:
        """Agent attempts to fix the incident. Returns (success, message)."""
        if not self.active:
            return False, "No active incident to remediate."

        correct_action, correct_service = CORRECT_REMEDIATION.get(
            self.incident_type, (None, None)
        )

        if action_type == correct_action and (service == correct_service or service is None):
            self.correct_remediation = True
            self.resolved = True
            self.active = False
            self.cascade_level = 0
            self.affected_services = []
            return True, f"Incident resolved. Root cause was '{self.incident_type}'. System recovering."
        else:
            self.wrong_attempts += 1
            return False, (
                f"Action '{action_type}' on '{service}' did not resolve '{self.incident_type}'. "
                f"Wrong attempts: {self.wrong_attempts}. Investigate further."
            )

    def get_latency_multiplier(self) -> float:
        """How much the incident multiplies baseline latency."""
        if not self.active:
            return 1.0
        multipliers = {0: 1.0, 1: 1.8, 2: 3.0, 3: 5.0}
        return multipliers.get(self.cascade_level, 1.0)

    def get_cascade_type(self) -> Optional[str]:
        """Return incident type for simulator to apply."""
        if not self.active:
            return None
        return self.incident_type

    def get_cascade_service(self) -> Optional[str]:
        """Return affected service for simulator."""
        if not self.active:
            return None
        return self.incident_service

    def recovery_score(self, current_step: int, max_steps: int) -> float:
        if not self.resolved or self.injected_step is None:
            return 0.0
        steps_to_resolve = (self.resolved_step or current_step) - self.injected_step
        max_recovery = max_steps * 0.4
        speed = max(0.0, 1.0 - steps_to_resolve / max_recovery)
        log_bonus = 0.1 if self.logs_read else 0.0
        wrong_penalty = min(0.3, self.wrong_attempts * 0.05)
        return max(0.0, min(1.0, speed + log_bonus - wrong_penalty))
