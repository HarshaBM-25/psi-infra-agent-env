"""
reward_utils.py — Multi-signal reward function.
Balances latency improvement, SLA recovery, stability, and cost.
Always returns values in [0.0, 1.0]. Never binary.
"""

from env.schemas import InfraReward


class RewardCalculator:

    def compute(
        self,
        latency: float,
        p99_latency: float,
        sla_ms: float,
        total_replicas: int,
        stable_steps: int,
        incident_active: bool,
        fix_attempted: bool,
        fix_success: bool,
        wrong_attempts: int,
        logs_read: bool,
        task_id: str,
    ) -> InfraReward:

        # --- Latency score (40%) ---
        if latency <= sla_ms:
            latency_score = 0.40
        elif latency <= sla_ms * 1.5:
            ratio = 1.0 - (latency - sla_ms) / (sla_ms * 0.5)
            latency_score = 0.40 * ratio * 0.6
        else:
            breach = min(latency / (sla_ms * 5), 1.0)
            latency_score = -0.25 * breach

        # --- SLA P99 score (10%) ---
        if p99_latency <= sla_ms * 1.5:
            sla_score = 0.10
        elif p99_latency <= sla_ms * 3:
            sla_score = 0.05
        else:
            sla_score = -0.05

        # --- Cost score (20%) ---
        max_replicas = 50
        min_replicas = 5
        cost_ratio = max(0.0, (max_replicas - total_replicas) / (max_replicas - min_replicas))
        cost_score = 0.20 * cost_ratio

        # --- Stability score (10%) ---
        stability_score = 0.0
        if stable_steps >= 3:
            stability_score = 0.10 * min(stable_steps / 15, 1.0)

        # --- Recovery score (20%) ---
        recovery_score = 0.0
        penalty = 0.0

        if incident_active:
            recovery_score -= 0.05  # penalize ignoring active incident

        if fix_attempted:
            if fix_success:
                base = 0.20
                if logs_read:
                    base += 0.05
                recovery_score = base
            else:
                penalty += 0.04 * min(wrong_attempts, 5)

        # --- Total ---
        total = (
            latency_score + sla_score + cost_score +
            stability_score + recovery_score - penalty
        )
        total = round(max(0.0, min(1.0, total)), 4)

        return InfraReward(
            total=total,
            latency_score=round(latency_score, 4),
            sla_score=round(sla_score, 4),
            cost_score=round(cost_score, 4),
            stability_score=round(stability_score, 4),
            recovery_score=round(recovery_score, 4),
            penalty=round(penalty, 4),
        )
