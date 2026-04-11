"""
infra_utils.py — Observation helpers: alert detection and LLM-friendly summary builder.
"""

from typing import List, Optional, Tuple
from env.schemas import ServiceMetrics


def get_alert(
    latency: float,
    sla_ms: float,
    incident_active: bool,
    incident_type: Optional[str],
    queue_size: int,
    db_connections: int,
) -> Tuple[str, str]:
    """Return (alert_level, alert_message)."""
    if incident_active and incident_type:
        return "critical", f"ACTIVE INCIDENT: {incident_type}. Immediate action required."
    if latency > sla_ms * 2:
        return "critical", f"Latency {latency:.0f}ms is {latency/sla_ms:.1f}x SLA threshold. SLA severely breached."
    if latency > sla_ms:
        return "warning", f"Latency {latency:.0f}ms exceeds SLA of {sla_ms:.0f}ms."
    if queue_size > 3000:
        return "warning", f"Queue depth {queue_size} approaching limit. Risk of backpressure."
    if db_connections > 150:
        return "warning", f"DB connections {db_connections}/200. Pool near saturation."
    return "none", "All systems nominal."


def build_summary(
    time_step: int,
    task_id: str,
    rps: float,
    latency: float,
    p99: float,
    sla_ms: float,
    services: List[ServiceMetrics],
    queue_size: int,
    db_connections: int,
    cache_hit_rate: float,
    incident_active: bool,
    incident_type: Optional[str],
    cascade_level: int,
    spike_warning: Optional[str],
    alert_level: str,
    alert_msg: str,
) -> str:
    """Build natural language summary for LLM agent consumption."""
    lines = []
    lines.append(f"[Step {time_step}] Task: {task_id}")
    lines.append(f"Traffic: {rps:.0f} req/s | Latency: {latency:.0f}ms (P99: {p99:.0f}ms) | SLA: {sla_ms:.0f}ms")

    sla_status = "OK" if latency <= sla_ms else f"BREACHED by {latency - sla_ms:.0f}ms"
    lines.append(f"SLA Status: {sla_status}")

    lines.append(f"Queue depth: {queue_size} | DB connections: {db_connections}/200 | Cache hit: {cache_hit_rate:.0%}")

    lines.append("Services:")
    for svc in services:
        status_icon = {"healthy": "✓", "degraded": "!", "overloaded": "!!", "down": "✗"}.get(svc.status, "?")
        lines.append(
            f"  [{status_icon}] {svc.name}: {svc.replicas} replicas | CPU {svc.cpu_percent:.0f}% | "
            f"Latency {svc.latency_ms:.0f}ms | Errors {svc.error_rate:.1%} | {svc.status}"
        )

    if incident_active and incident_type:
        lines.append(f"INCIDENT ACTIVE: {incident_type} (cascade level {cascade_level}/3)")
        lines.append("→ Use read_logs action to investigate, then apply the correct remediation.")

    if spike_warning:
        lines.append(f"SPIKE WARNING: {spike_warning}")

    if alert_level != "none":
        lines.append(f"ALERT [{alert_level.upper()}]: {alert_msg}")

    lines.append("")
    lines.append("Available actions:")
    lines.append("  scale_service(service, value)  — add/remove replicas: api, auth, db, cache, queue")
    lines.append("  restart_service(service)       — restart a crashed/degraded service")
    lines.append("  reroute_traffic(service)       — redirect traffic away from degraded service")
    lines.append("  clear_queue(queue)             — drain the message queue backlog")
    lines.append("  adjust_cache(cache)            — boost cache hit rate")
    lines.append("  do_nothing                     — hold current state")

    return "\n".join(lines)
