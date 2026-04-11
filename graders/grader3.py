"""grader3.py — Task 3: Root Cause Diagnosis grader."""
from typing import List, Optional


def grade(
    episode_rewards: List[float],
    sla_breaches: int,
    total_steps: int,
    root_cause_identified: bool,
    correct_remediation: bool,
    logs_read: bool,
    wrong_attempts: int,
    injected_step: int,
    resolved_step: Optional[int],
    cascade_contained: bool,
) -> float:
    if not episode_rewards:
        return 0.0
    avg_reward = sum(episode_rewards) / len(episode_rewards)
    sla_rate = 1.0 - (sla_breaches / max(total_steps, 1))
    diagnosis_score = 0.0
    if root_cause_identified and correct_remediation:
        diagnosis_score = 0.4
        if logs_read:
            diagnosis_score += 0.05
        if resolved_step:
            speed = max(0.0, 1.0 - (resolved_step - injected_step) / 60)
            diagnosis_score += 0.1 * speed
        diagnosis_score -= min(0.15, wrong_attempts * 0.03)
    cascade_bonus = 0.05 if cascade_contained else 0.0
    score = (0.25 * avg_reward + 0.25 * sla_rate + 0.4 * diagnosis_score + cascade_bonus)
    return round(max(0.0, min(1.0, score)), 4)
