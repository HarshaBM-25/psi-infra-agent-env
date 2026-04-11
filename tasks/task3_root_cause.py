"""
task3_root_cause.py — Hard: Multiple symptoms, cascading failures. Find the root cause.
Agent must reason over correlated symptoms across services to identify root cause.
"""
TASK_ID = "task3_root_cause"
MAX_STEPS = 200
DIFFICULTY = "hard"

DESCRIPTION = """
Task 3 — Root Cause Diagnosis (Hard)

Multiple failures cascade across services simultaneously.
At step 35 a primary incident is injected.
At step 60 a secondary cascading failure compounds it.

The agent must:
  1. Distinguish root cause from cascading symptoms
  2. Read logs to confirm the hypothesis
  3. Apply the correct targeted remediation (not just scale everything)
  4. Handle the cascade without worsening it
  5. Maintain SLA throughout the diagnosis process

Failure chain example:
  cache_invalidation → DB connection surge → Auth latency → API timeout

Scoring:
  0.0 → scales randomly, never resolves root cause
  0.3 → resolves one incident but misses cascade
  0.7 → correct root cause, partial cascade handling
  1.0 → correct diagnosis, fast resolution, SLA maintained
"""
