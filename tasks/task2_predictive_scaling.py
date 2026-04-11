"""
task2_predictive_scaling.py — Medium: Traffic ramping up. Pre-scale before it hits.
Agent receives early warnings and must anticipate demand, not just react.
"""
TASK_ID = "task2_predictive_scaling"
MAX_STEPS = 150
DIFFICULTY = "medium"

DESCRIPTION = """
Task 2 — Predictive Autoscaling (Medium)

Traffic gradually ramps up with two major surges at step ~60 and ~110.
The agent receives spike warnings 7 steps before each surge.
Reacting after the surge causes SLA breach. Pre-scaling is required.

An additional incident is injected at step 50 (during the ramp)
making the timing more challenging.

Scoring:
  0.0 → reactive only, SLA breached on every surge
  0.5 → pre-scales correctly but incident handling fails
  1.0 → pre-scales, handles incident, zero SLA breach
"""
