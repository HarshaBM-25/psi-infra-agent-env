"""
task1_incident_recovery.py — Easy: System already degraded. Recover it.
Agent starts with an active incident and must restore SLA within max_steps.
"""
TASK_ID = "task1_incident_recovery"
MAX_STEPS = 100
DIFFICULTY = "easy"

DESCRIPTION = """
Task 1 — Reactive Incident Recovery (Easy)

The system is already degraded when the episode begins.
An incident is injected at step 1. The agent must:
  1. Observe the degraded metrics
  2. Investigate (read_logs or observe symptoms)
  3. Apply the correct remediation
  4. Scale services to handle the load
  5. Maintain SLA for the remainder of the episode

Scoring:
  0.0 → ignores incident, SLA breached throughout
  0.5 → resolves incident but takes many wrong attempts
  1.0 → fast correct remediation, SLA restored and maintained
"""
