"""grader2.py — Task 2: Predictive Autoscaling grader."""
from typing import List


def grade(
    episode_rewards: List[float],
    sla_breaches: int,
    total_steps: int,
    surge_breaches: int,
    pre_scaled: bool,
    incident_resolved: bool,
) -> float:
    if not episode_rewards:
        return 0.0
    avg_reward = sum(episode_rewards) / len(episode_rewards)
    sla_rate = 1.0 - (sla_breaches / max(total_steps, 1))
    surge_windows = 40
    surge_score = 1.0 - (surge_breaches / max(surge_windows, 1))
    pre_scale_bonus = 0.1 if pre_scaled else 0.0
    resolution_bonus = 0.1 if incident_resolved else 0.0
    score = (0.3 * avg_reward + 0.25 * sla_rate + 0.25 * surge_score
             + pre_scale_bonus + resolution_bonus)
    return round(max(0.0, min(1.0, score)), 4)
