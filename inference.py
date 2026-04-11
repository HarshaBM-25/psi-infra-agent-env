"""
inference.py — InfraAgent-Env v2 inference script.
Hackathon compliant: [START] [STEP] [END] format.
Uses OpenAI client. Falls back to heuristic if LLM quota exhausted.
"""

import asyncio
import json
import os
import textwrap
from typing import List, Optional

import httpx
from openai import OpenAI

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME   = os.getenv("MODEL_NAME",   "Qwen/Qwen2.5-72B-Instruct")
HF_TOKEN     = os.getenv("HF_TOKEN")
ENV_BASE_URL = os.getenv("ENV_BASE_URL", "http://localhost:7860")
BENCHMARK    = "infra-agent-env-v2"

if not HF_TOKEN:
    raise ValueError("HF_TOKEN environment variable is required but not set.")

TASKS = [
    "task1_incident_recovery",
    "task2_predictive_scaling",
    "task3_root_cause",
]

MAX_STEPS = {
    "task1_incident_recovery":  100,
    "task2_predictive_scaling": 150,
    "task3_root_cause":         200,
}

SUCCESS_THRESHOLD = 0.35
_llm_quota_exhausted = False


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    err = error if error else "null"
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={str(done).lower()} error={err}", flush=True)


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}", flush=True)


SYSTEM_PROMPT = textwrap.dedent("""
You are an autonomous Site Reliability Engineer managing a microservice cluster.
Services: api, auth, db, cache, queue. SLA: keep latency under 200ms.

Actions — respond with ONE JSON object only:
{"action_type": "scale_service",   "service": "<n>", "value": <int>}
{"action_type": "restart_service", "service": "<n>"}
{"action_type": "reroute_traffic", "service": "<n>"}
{"action_type": "clear_queue",     "service": "queue"}
{"action_type": "adjust_cache",    "service": "cache"}
{"action_type": "do_nothing"}

Incident fix map:
  service_crash      -> restart_service api
  db_overload        -> scale_service db value=2
  queue_flood        -> clear_queue queue
  cache_invalidation -> adjust_cache cache
  auth_degraded      -> restart_service auth

Rules:
- INCIDENT ACTIVE? Apply targeted fix immediately.
- latency > 200ms? scale_service api value=2
- spike_warning? scale_service api value=3 NOW
- queue_size > 3000? clear_queue queue
- db_connections > 150? scale_service db value=2
- cache_hit_rate < 0.5? adjust_cache cache
- latency < 80ms and api replicas > 3? scale_service api value=-1

JSON only. No markdown. No explanation.
""").strip()


def get_llm_action(client: OpenAI, observation: dict, history: List[str]) -> Optional[dict]:
    global _llm_quota_exhausted
    if _llm_quota_exhausted:
        return None

    services_text = "\n".join(
        f"  {s['name']}: replicas={s['replicas']} latency={s['latency_ms']:.0f}ms "
        f"cpu={s['cpu_percent']:.0f}% errors={s['error_rate']:.1%} status={s['status']}"
        for s in observation.get("services", [])
    )

    user_msg = (
        f"Step {observation.get('time_step',0)} | "
        f"RPS={observation.get('total_rps',0):.0f} | "
        f"Latency={observation.get('avg_latency_ms',0):.0f}ms | "
        f"SLA_breach={observation.get('sla_breach',False)}\n"
        f"Queue={observation.get('queue_size',0)} | "
        f"DB_conn={observation.get('db_connections',0)}/200 | "
        f"Cache_hit={observation.get('cache_hit_rate',0):.1%}\n"
        f"Alert[{observation.get('alert_level','none').upper()}]: {observation.get('alert_message','')}\n"
        f"Spike warning: {observation.get('spike_warning','none')}\n"
        f"Services:\n{services_text}\n"
        f"Last actions: {', '.join(history[-3:]) if history else 'none'}\n"
        f"Choose action (JSON only):"
    )

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": user_msg},
            ],
            temperature=0.1,
            max_tokens=80,
        )
        text = (response.choices[0].message.content or "").strip()
        text = text.replace("```json", "").replace("```", "").strip()
        return json.loads(text)
    except Exception as e:
        err_str = str(e)
        if "402" in err_str or "credits" in err_str.lower() or "quota" in err_str.lower():
            print("[DEBUG] LLM quota exhausted. Using heuristic agent.", flush=True)
            _llm_quota_exhausted = True
        else:
            print(f"[DEBUG] LLM error: {e}", flush=True)
        return None


def heuristic_action(observation: dict) -> dict:
    latency   = observation.get("avg_latency_ms", 0)
    alert_msg = observation.get("alert_message", "")
    alert     = observation.get("alert_level", "none")
    queue     = observation.get("queue_size", 0)
    db_conn   = observation.get("db_connections", 0)
    cache_hit = observation.get("cache_hit_rate", 0.85)
    spike_w   = observation.get("spike_warning")
    services  = {s["name"]: s for s in observation.get("services", [])}
    api_rep   = services.get("api", {}).get("replicas", 3)

    if alert in ("critical", "warning") or "INCIDENT" in alert_msg:
        if "queue_flood" in alert_msg or queue > 3000:
            return {"action_type": "clear_queue", "service": "queue"}
        if "db_overload" in alert_msg or db_conn > 150:
            return {"action_type": "scale_service", "service": "db", "value": 2}
        if "cache_invalidation" in alert_msg or cache_hit < 0.4:
            return {"action_type": "adjust_cache", "service": "cache"}
        if "service_crash" in alert_msg:
            return {"action_type": "restart_service", "service": "api"}
        if "auth_degraded" in alert_msg:
            return {"action_type": "restart_service", "service": "auth"}

    if spike_w and api_rep < 8:
        return {"action_type": "scale_service", "service": "api", "value": 3}
    if latency > 200 and api_rep < 10:
        return {"action_type": "scale_service", "service": "api", "value": 2}
    if latency < 80 and api_rep > 2:
        return {"action_type": "scale_service", "service": "api", "value": -1}
    return {"action_type": "do_nothing"}


VALID_ACTIONS = {
    "scale_service", "restart_service", "reroute_traffic",
    "clear_queue", "adjust_cache", "do_nothing",
}


def choose_action(client: OpenAI, observation: dict, history: List[str]) -> dict:
    action = get_llm_action(client, observation, history)
    if action and isinstance(action, dict) and action.get("action_type") in VALID_ACTIONS:
        return action
    return heuristic_action(observation)


async def wait_for_env(retries: int = 20, delay: float = 3.0) -> bool:
    for i in range(retries):
        try:
            async with httpx.AsyncClient(base_url=ENV_BASE_URL, timeout=10) as http:
                r = await http.get("/health")
                if r.status_code == 200:
                    print(f"[DEBUG] Server ready (attempt {i+1})", flush=True)
                    return True
        except Exception:
            pass
        await asyncio.sleep(delay)
    return False


async def run_task(client: OpenAI, task_id: str) -> float:
    global _llm_quota_exhausted
    _llm_quota_exhausted = False

    log_start(task=task_id, env=BENCHMARK, model=MODEL_NAME)

    rewards: List[float] = []
    history: List[str]   = []
    steps_taken = 0

    try:
        async with httpx.AsyncClient(base_url=ENV_BASE_URL, timeout=60.0) as http:

            reset_resp = await http.post(
                "/reset",
                params={"task_id": task_id, "seed": 42},
            )
            reset_resp.raise_for_status()
            observation = reset_resp.json().get("observation", {})

            for step in range(1, MAX_STEPS[task_id] + 1):

                action_dict = choose_action(client, observation, history)
                action_str  = json.dumps(action_dict)

                try:
                    step_resp = await http.post("/step", json=action_dict, timeout=30.0)
                    step_resp.raise_for_status()
                    step_data = step_resp.json()
                except Exception as e:
                    log_step(step, action_str, 0.0, True, str(e))
                    break

                reward      = float(step_data.get("reward", 0.0))
                done        = bool(step_data.get("done", False))
                observation = step_data.get("observation", {})
                fix_msg     = step_data.get("info", {}).get("fix_message")

                rewards.append(reward)
                steps_taken = step

                log_step(
                    step=step,
                    action=action_str,
                    reward=reward,
                    done=done,
                    error=fix_msg if fix_msg and "did not resolve" in str(fix_msg) else None,
                )

                history.append(f"step={step} {action_dict.get('action_type')} r={reward:.2f}")

                if done:
                    break

    except Exception as e:
        print(f"[DEBUG] Task {task_id} exception: {e}", flush=True)

    # ----------------------------------------------------------------
    # KEY FIX: score computed HERE outside try/finally
    # Previously was inside finally block which caused scope issue
    # returning outer score=0.0 instead of computed value
    # ----------------------------------------------------------------
    score   = round(sum(rewards) / max(len(rewards), 1), 3)
    score   = max(0.0, min(1.0, score))
    success = score >= SUCCESS_THRESHOLD

    log_end(success=success, steps=steps_taken, score=score, rewards=rewards)
    return score


async def main() -> None:
    print(f"[DEBUG] ENV_BASE_URL = {ENV_BASE_URL}", flush=True)
    print(f"[DEBUG] MODEL_NAME   = {MODEL_NAME}",   flush=True)
    print(f"[DEBUG] API_BASE_URL = {API_BASE_URL}",  flush=True)

    client = OpenAI(base_url=API_BASE_URL, api_key=HF_TOKEN)

    print("[DEBUG] Waiting for environment server...", flush=True)
    ready = await wait_for_env()
    if not ready:
        print("[DEBUG] WARNING: Server not confirmed ready. Proceeding.", flush=True)

    scores = {}
    for task_id in TASKS:
        score = await run_task(client, task_id)
        scores[task_id] = score

    print("\n===== FINAL SCORES =====", flush=True)
    for task, s in scores.items():
        print(f"  {task}: {s:.3f}", flush=True)
    print("========================", flush=True)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"[DEBUG] Fatal: {e}", flush=True)
        raise