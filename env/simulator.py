"""
simulator.py — Microservice-aware infrastructure simulator
Models: API gateway → Auth → DB with queue buildup and cascading failures.
Pure math — no ML, no heavy deps. Runs comfortably under 8GB RAM.
"""

import math
import random
from typing import Dict, List, Tuple
from collections import deque


# Service dependency graph: downstream services each service depends on
DEPENDENCY_GRAPH = {
    "api":   ["auth", "cache"],
    "auth":  ["db"],
    "cache": [],
    "db":    [],
    "queue": [],
}

SERVICE_NAMES = ["api", "auth", "db", "cache", "queue"]

# Baseline capacity per replica (rps)
REPLICA_CAPACITY = {
    "api":   300,
    "auth":  400,
    "db":    200,
    "cache": 800,
    "queue": 500,
}

# Base latency contribution per service (ms)
BASE_LATENCY = {
    "api":   15,
    "auth":  10,
    "db":    20,
    "cache": 5,
    "queue": 8,
}

MAX_QUEUE = 5000
MAX_DB_CONNECTIONS = 200


class MicroserviceSimulator:
    """
    Simulates a microservice cluster with:
    - Per-service CPU, latency, queue size
    - Cascading failure propagation
    - Database connection pool pressure
    - Cache hit/miss impact on latency
    - Queue buildup causing backpressure
    """

    def __init__(self, seed: int = 42):
        self.seed = seed
        self._rng = random.Random(seed)
        self.reset()

    def reset(self):
        self._rng = random.Random(self.seed)
        # Replicas per service
        self.replicas: Dict[str, int] = {
            "api":   3,
            "auth":  2,
            "db":    2,
            "cache": 2,
            "queue": 2,
        }
        # Service health flags
        self.service_down: Dict[str, bool] = {s: False for s in SERVICE_NAMES}
        self.queue_size: int = 0
        self.db_connections: int = 0
        self.cache_hit_rate: float = 0.85
        self._latency_history: deque = deque([30.0] * 10, maxlen=10)

    def step(
        self,
        rps: float,
        action_type: str,
        action_service: str,
        action_value: int,
        incident_type: str,
        incident_service: str,
    ) -> Dict:
        """
        Advance simulation one step.
        Returns dict of per-service metrics + global metrics.
        """
        # Apply action
        self._apply_action(action_type, action_service, action_value)

        # Apply incident effects
        self._apply_incident(incident_type, incident_service)

        # Simulate queue buildup
        self._update_queue(rps)

        # Simulate DB pressure
        self._update_db_connections(rps)

        # Simulate cache pressure
        self._update_cache(rps)

        # Compute per-service metrics
        service_metrics = {}
        for svc in SERVICE_NAMES:
            metrics = self._compute_service_metrics(svc, rps)
            service_metrics[svc] = metrics

        # Compute end-to-end latency (API → Auth → DB chain)
        e2e_latency = self._compute_e2e_latency(service_metrics, rps)
        self._latency_history.append(e2e_latency)

        # P99 latency (95th percentile approximation from history)
        sorted_hist = sorted(self._latency_history)
        p99_idx = max(0, int(len(sorted_hist) * 0.95) - 1)
        p99_latency = sorted_hist[p99_idx]

        # Global CPU (weighted average)
        total_replicas = sum(self.replicas.values())
        avg_cpu = sum(
            service_metrics[s]["cpu"] * self.replicas[s]
            for s in SERVICE_NAMES
        ) / max(total_replicas, 1)

        return {
            "service_metrics": service_metrics,
            "avg_latency_ms": round(e2e_latency, 1),
            "p99_latency_ms": round(p99_latency, 1),
            "avg_cpu": round(avg_cpu, 1),
            "queue_size": self.queue_size,
            "db_connections": self.db_connections,
            "cache_hit_rate": round(self.cache_hit_rate, 3),
            "latency_history": list(self._latency_history),
            "cost_per_step": self._compute_cost(),
        }

    def _apply_action(self, action_type: str, service: str, value: int):
        if service not in SERVICE_NAMES:
            return
        if action_type == "scale_service":
            self.replicas[service] = max(1, min(10, self.replicas[service] + value))
        elif action_type == "restart_service":
            self.service_down[service] = False
            self.replicas[service] = max(1, self.replicas[service])
        elif action_type == "clear_queue":
            self.queue_size = max(0, self.queue_size - 1000)
        elif action_type == "adjust_cache":
            self.cache_hit_rate = min(0.99, self.cache_hit_rate + 0.1)
        elif action_type == "reroute_traffic":
            # Rerouting reduces load on degraded service temporarily
            if self.service_down.get(service):
                self.service_down[service] = False

    def _apply_incident(self, incident_type: str, incident_service: str):
        if incident_type == "none" or not incident_service:
            return
        if incident_type == "service_crash":
            self.service_down[incident_service] = True
        elif incident_type == "db_overload":
            self.db_connections = min(MAX_DB_CONNECTIONS, self.db_connections + 30)
        elif incident_type == "queue_flood":
            self.queue_size = min(MAX_QUEUE, self.queue_size + 500)
        elif incident_type == "cache_invalidation":
            self.cache_hit_rate = max(0.1, self.cache_hit_rate - 0.3)

    def _update_queue(self, rps: float):
        api_capacity = self.replicas["api"] * REPLICA_CAPACITY["api"]
        overflow = max(0, rps - api_capacity)
        # Queue grows when overflow, drains when capacity available
        drain = max(0, api_capacity - rps) * 0.3
        self.queue_size = max(0, min(MAX_QUEUE, self.queue_size + overflow * 0.1 - drain))
        self.queue_size = int(self.queue_size)

    def _update_db_connections(self, rps: float):
        db_capacity = self.replicas["db"] * REPLICA_CAPACITY["db"]
        # Each request that hits DB (miss on cache) needs a connection
        db_load = rps * (1 - self.cache_hit_rate)
        target_connections = min(MAX_DB_CONNECTIONS, int(db_load / max(db_capacity, 1) * 100))
        # Smooth transition
        self.db_connections = int(0.7 * self.db_connections + 0.3 * target_connections)

    def _update_cache(self, rps: float):
        cache_capacity = self.replicas["cache"] * REPLICA_CAPACITY["cache"]
        if rps > cache_capacity:
            # Cache under pressure — hit rate degrades
            self.cache_hit_rate = max(0.3, self.cache_hit_rate - 0.02)
        else:
            # Cache recovers slowly
            self.cache_hit_rate = min(0.95, self.cache_hit_rate + 0.005)

    def _compute_service_metrics(self, service: str, rps: float) -> Dict:
        if self.service_down[service]:
            return {
                "cpu": 0.0,
                "latency_ms": 9999.0,
                "queue_size": 0,
                "error_rate": 1.0,
                "status": "down",
                "replicas": self.replicas[service],
            }

        capacity = self.replicas[service] * REPLICA_CAPACITY[service]
        load_ratio = rps / max(capacity, 1)

        # CPU — linear with load
        cpu = min(100.0, 5 + load_ratio * 90 + self._rng.gauss(0, 2))

        # Latency — exponential degradation
        base = BASE_LATENCY[service]
        if load_ratio <= 1.0:
            latency = base + (load_ratio ** 1.5) * base * 4
        else:
            latency = base + base * 4 + ((load_ratio - 1.0) ** 2) * base * 20

        # Queue pressure adds to DB latency
        if service == "db":
            queue_pressure = (self.queue_size / MAX_QUEUE) * 200
            latency += queue_pressure
            conn_pressure = (self.db_connections / MAX_DB_CONNECTIONS) * 150
            latency += conn_pressure

        # Cache miss penalty on API latency
        if service == "api":
            cache_miss_penalty = (1 - self.cache_hit_rate) * 50
            latency += cache_miss_penalty

        latency += self._rng.gauss(0, 5)
        latency = max(base, latency)

        # Error rate rises sharply when overloaded
        error_rate = min(1.0, max(0.0, (load_ratio - 0.8) * 0.5)) if load_ratio > 0.8 else 0.0

        # Status classification
        if load_ratio > 1.5:
            status = "overloaded"
        elif load_ratio > 0.8 or error_rate > 0.05:
            status = "degraded"
        else:
            status = "healthy"

        return {
            "cpu": round(cpu, 1),
            "latency_ms": round(latency, 1),
            "queue_size": self.queue_size if service == "queue" else 0,
            "error_rate": round(error_rate, 3),
            "status": status,
            "replicas": self.replicas[service],
        }

    def _compute_e2e_latency(self, service_metrics: Dict, rps: float) -> float:
        """
        End-to-end latency = API + Auth + DB (critical path).
        Cache hits short-circuit DB calls.
        """
        api_lat  = service_metrics["api"]["latency_ms"]
        auth_lat = service_metrics["auth"]["latency_ms"]
        db_lat   = service_metrics["db"]["latency_ms"]

        # Cache hits reduce DB calls
        effective_db = db_lat * (1 - self.cache_hit_rate)

        # If any service is down, latency spikes
        if (service_metrics["api"]["status"] == "down" or
                service_metrics["auth"]["status"] == "down"):
            return 9999.0

        e2e = api_lat + auth_lat * 0.6 + effective_db * 0.4
        # Queue backlog adds tail latency
        e2e += (self.queue_size / MAX_QUEUE) * 300
        return round(e2e, 1)

    def _compute_cost(self) -> float:
        """Cost per step: $0.05 per replica per step."""
        total_replicas = sum(self.replicas.values())
        return round(total_replicas * 0.05, 4)


class TrafficSimulator:
    """
    Realistic traffic patterns per task.
    Deterministic given seed for reproducibility.
    """

    def __init__(self, task_id: str, seed: int = 42):
        self.task_id = task_id
        self.seed = seed
        self._rng = random.Random(seed)
        self._step = 0

    def reset(self):
        self._rng = random.Random(self.seed)
        self._step = 0

    def get_rps(self, t: int) -> float:
        self._step = t
        if self.task_id == "task1_incident_recovery":
            return self._steady_high(t)
        elif self.task_id == "task2_predictive_scaling":
            return self._surge_pattern(t)
        elif self.task_id == "task3_root_cause":
            return self._multi_spike(t)
        return self._steady_high(t)

    def _steady_high(self, t: int) -> float:
        """Task 1: Already-degraded system. High steady traffic."""
        base = 900
        noise = self._rng.gauss(0, 40)
        return max(200, base + noise)

    def _surge_pattern(self, t: int) -> float:
        """Task 2: Gradual build-up then sudden surge."""
        base = 300
        ramp = min(t * 8, 600)  # ramps up over first 75 steps
        spike = 0
        if 60 <= t <= 80:
            spike = 1200
        elif 110 <= t <= 130:
            spike = 1800
        noise = self._rng.gauss(0, 60)
        return max(100, base + ramp + spike + noise)

    def _multi_spike(self, t: int) -> float:
        """Task 3: Multiple simultaneous symptoms."""
        base = 700
        wave = 400 * math.sin(t / 25 * math.pi)
        burst = 0
        if 40 <= t <= 55:
            burst = 1000
        if 90 <= t <= 110:
            burst = 1500
        noise = self._rng.gauss(0, 70)
        return max(200, base + wave + burst + noise)

    def get_spike_warning(self, t: int) -> str:
        if self.task_id != "task2_predictive_scaling":
            return None
        if 53 <= t <= 59:
            return "WARNING: Traffic ramp detected. Major surge in ~7 steps. Pre-scale now."
        if 103 <= t <= 109:
            return "WARNING: Second surge incoming. System approaching capacity limits."
        return None

    def get_traffic_trend(self, t: int) -> str:
        if self.task_id == "task2_predictive_scaling":
            if t < 75:
                return "rising"
            if 60 <= t <= 80 or 110 <= t <= 130:
                return "surging"
        rps_now  = self.get_rps(t)
        rps_prev = self.get_rps(max(0, t - 3))
        delta = rps_now - rps_prev
        if delta > 80:
            return "rising"
        if delta < -80:
            return "falling"
        return "stable"
