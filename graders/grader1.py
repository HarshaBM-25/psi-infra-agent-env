"""grader1.py — Task 1: Reactive Incident Recovery grader."""
from typing import List


def grade(
    episode_rewards: List[float],
    sla_breaches: int,
    total_steps: int,
    incident_resolved: bool,
    correct_remediation: bool,
    wrong_attempts: int,
) -> float:
    if not episode_rewards:
        return 0.0
    avg_reward = sum(episode_rewards) / len(episode_rewards)
    sla_rate = 1.0 - (sla_breaches / max(total_steps, 1))
    resolution_score = 0.0
    if incident_resolved and correct_remediation:
        resolution_score = max(0.0, 0.4 - wrong_attempts * 0.05)
    score = 0.4 * avg_reward + 0.3 * sla_rate + 0.3 * resolution_score
    return round(max(0.0, min(1.0, score)), 4)
