# InfraAgent-Env v2.0

---
title: Infra Agent Environment
emoji: ⚙️
colorFrom: blue
colorTo: green
sdk: docker
app_port: 7860
pinned: false
---

**An autonomous Site Reliability Engineering (SRE) training environment powered by RL and LLMs.**

![Build](https://img.shields.io/badge/build-passing-brightgreen) ![Python](https://img.shields.io/badge/python-3.10+-blue) ![License](https://img.shields.io/badge/license-MIT-green)

---

## 🎯 Overview

**InfraAgent-Env** is a comprehensive reinforcement learning (RL) environment designed to train autonomous SRE agents to manage microservice infrastructure. It simulates realistic cloud infrastructure scenarios with multiple services, dynamic traffic patterns, incident injection, and cascading failures—all while enforcing SLA constraints.

The environment is **OpenEnv spec compliant** and provides both:
- **API-driven interface** (FastAPI server) for external agents
- **LLM integration** with fallback heuristics for autonomous decision-making

### Key Features

✅ **Microservice-aware simulation** (5 services: api, auth, db, cache, queue)  
✅ **Realistic incident injection** (crashes, overloads, queue floods, cache invalidation)  
✅ **Cascading failure modeling** (one incident triggering secondary failures)  
✅ **OpenEnv spec compliance** (`/reset`, `/step`, `/state` endpoints)  
✅ **LLM-ready prompts** with fallback to heuristic policies  
✅ **Three difficulty levels** with progressive complexity  
✅ **Docker support** for easy deployment  
✅ **Interactive dashboard** for real-time monitoring  

---

## 📋 Tasks

The environment features **three progressive tasks** that increase in difficulty:

### Task 1: Incident Recovery (Easy) — 100 steps max

**Scenario**: The system is already degraded when the episode starts. An incident is injected at step 1.

**Agent Objective**:
1. Observe degraded metrics
2. Diagnose the incident
3. Apply targeted remediation
4. Scale services and restore SLA

**Scoring**: 0.0 (fails) → 1.0 (fast recovery, SLA maintained)

---

### Task 2: Predictive Autoscaling (Medium) — 150 steps max

**Scenario**: Traffic ramps up gradually with two major surges at ~step 60 and ~110. Spike warnings arrive 7 steps in advance.

**Agent Objective**:
1. Recognize early spike warnings
2. **Pre-scale services before surge hits** (reactive scaling fails)
3. Handle an incident injected at step 50 during the ramp
4. Maintain SLA without excessive scaling

**Scoring**: 0.0 (reactive only) → 1.0 (perfect anticipation)

---

### Task 3: Root Cause Diagnosis (Hard) — 200 steps max

**Scenario**: Multiple cascading failures occur simultaneously. Primary incident at step 35, secondary cascade at step 60.

**Agent Objective**:
1. Distinguish **root cause** from cascading symptoms
2. Read logs to confirm hypothesis
3. Apply **targeted remediation** (not just scale)
4. Handle cascades without worsening them
5. Maintain SLA throughout

**Example cascade**: `cache_invalidation → DB surge → auth latency → API timeout`

**Scoring**: 0.0 (random scaling) → 1.0 (correct diagnosis, fast resolution)

---

## 🏗️ Architecture

```
infra-agent-env/
├── env/                          # Core RL environment
│   ├── infra_env.py              # Main OpenEnv interface (reset/step/state)
│   ├── schemas.py                # Pydantic models (Action, Observation, Reward)
│   ├── simulator.py              # Microservice & traffic simulators
│   ├── incident_engine.py        # Incident injection & cascading logic
│
├── tasks/                        # Task specifications
│   ├── task1_incident_recovery.py
│   ├── task2_predictive_scaling.py
│   ├── task3_root_cause.py
│
├── agents/                       # Reference agents
│   ├── random_agent.py           # Random baseline
│   ├── rule_agent.py             # Heuristic-based policy
│
├── graders/                      # Scoring & evaluation
│   ├── grader1.py / grader2.py / grader3.py
│
├── main.py                       # FastAPI server
├── inference.py                  # LLM inference loop (hackathon-ready)
├── utils/
│   ├── infra_utils.py            # Observation summaries, alerts
│   ├── reward_utils.py           # SLA-based reward calculation
│
├── config/
│   └── env_config.yaml           # Service configs, SLA thresholds
│
└── dashboard/
    └── dashboard.html            # Real-time monitoring UI
```

---

## 🚀 Quick Start

### Installation

```bash
# Clone and enter directory
git clone <repo> && cd infra-agent-env

# Install dependencies
pip install -r requirements.txt

# Or with uv
uv sync
```

### Running the Server

```bash
# Start FastAPI server on http://localhost:7860
uvicorn main:app --reload

# Or in Docker
docker build -t infra-agent-env .
docker run -p 7860:7860 infra-agent-env
```

### Running Inference (LLM-based agent)

```bash
# Set required environment variables
export HF_TOKEN="your-huggingface-token"
export ENV_BASE_URL="http://localhost:7860"  # Adjust if needed
export TASK_ID="task1_incident_recovery"      # or task2, task3

# Run inference with LLM fallback to heuristics
python inference.py
```

**Output Format** (Hackathon compliant):
```
[START] task=task1_incident_recovery env=infra-agent-env model=Qwen/Qwen2.5-72B-Instruct
[STEP] step=1 action={"action_type":"restart_service","service":"api"} reward=0.42 done=false error=null
[STEP] step=2 action={"action_type":"scale_service","service":"api","value":2} reward=0.65 done=false error=null
...
[END] success=true steps=15 score=0.892 rewards=0.42,0.65,0.88,...
```

### Running Tests

```bash
pytest tests/ -v
```

---

## 📡 API Endpoints

All endpoints are **OpenEnv spec compliant**.

### 1. `GET /` — Dashboard
Serves the interactive real-time monitoring UI.
```bash
curl http://localhost:7860/
```

### 2. `POST /reset` — Reset Environment
```bash
curl -X POST "http://localhost:7860/reset?task_id=task1_incident_recovery&seed=42"

Response:
{
  "observation": {
    "time_step": 0,
    "total_rps": 100,
    "avg_latency_ms": 45.2,
    "services": [...],
    "alert_message": "System initialized",
    ...
  },
  "info": {"task_id": "task1_incident_recovery"}
}
```

### 3. `POST /step` — Execute Action
```bash
curl -X POST "http://localhost:7860/step" \
  -H "Content-Type: application/json" \
  -d '{
    "action_type": "scale_service",
    "service": "api",
    "value": 2
  }'

Response:
{
  "observation": {...},
  "reward": 0.45,
  "done": false,
  "info": {"fix_attempted": true, "fix_success": true}
}
```

### 4. `GET /state` — Get Current State
```bash
curl http://localhost:7860/state
```

### 5. `GET /health` — Health Check
```bash
curl http://localhost:7860/health
```

### 6. `GET /tasks` — List Available Tasks
```bash
curl http://localhost:7860/tasks
```

---

## 🎮 Action Space

The agent can perform one of 6 action types per step:

```python
{
  "action_type": "scale_service",      # Adjust replica count
  "service": "api|auth|db|cache|queue",
  "value": 1-10                         # New replica count
}

{
  "action_type": "restart_service",    # Restart a service
  "service": "api|auth|db|cache|queue"
}

{
  "action_type": "reroute_traffic",    # Reroute away from service
  "service": "api|auth|db|cache|queue"
}

{
  "action_type": "clear_queue",        # Drain queue backlog
  "service": "queue"
}

{
  "action_type": "adjust_cache",       # Clear & refresh cache
  "service": "cache"
}

{
  "action_type": "do_nothing"          # Hold steady
}
```

---

## 📊 Observation Space

Each step returns a rich observation containing:

```python
{
  # Global metrics
  "time_step": 42,
  "total_rps": 850.5,                  # Requests per second
  "avg_latency_ms": 145.3,             # Average latency
  "p99_latency_ms": 312.1,             # 99th percentile
  "sla_breach": false,                 # SLA = 200ms
  "cost_per_step": 0.45,               # Replica cost
  
  # Per-service snapshots
  "services": [
    {
      "name": "api",
      "replicas": 3,
      "cpu_percent": 72.5,
      "latency_ms": 120.0,
      "queue_size": 0,
      "error_rate": 0.001,
      "status": "healthy"
    },
    ...
  ],
  
  # Resource pressure
  "queue_size": 250,
  "db_connections": 95,
  "cache_hit_rate": 0.87,
  
  # Trend detection
  "latency_history": [100, 105, 110, ...],  # Last 10 steps
  "traffic_trend": "ramping",
  "spike_warning": "spike predicted in 7 steps",
  
  # Alerts for LLM
  "alert_level": "warning",
  "alert_message": "Latency trending up. Spike warning active.",
  
  # Human-readable summary
  "summary": "3 api replicas, 120ms latency. Warning: spike predicted."
}
```

---

## 🎯 Reward Function

The reward is a composite SLA-based score:

$$\text{Reward} = \text{incident\_fix\_bonus} + \text{latency\_penalty} - \text{cost\_penalty} + \text{stability\_bonus}$$

- **Incident fix bonus**: +0.5 when successfully remediating an incident
- **Latency penalty**: Proportional to SLA breach (target: 200ms)
- **Cost penalty**: 0.05 per extra replica beyond baseline
- **Stability bonus**: +0.1 per step without action changes

**Perfect score**: 1.0 (zero SLA breach, correct incident handling, minimal cost)

---

## 🧠 LLM System Prompt

The inference script uses a sophisticated system prompt for autonomous decision-making:

```
You are an autonomous Site Reliability Engineer managing a microservice cluster.
Services: api, auth, db, cache, queue. SLA: keep latency under 200ms.

Rules:
  • INCIDENT ACTIVE? Apply targeted fix immediately.
  • latency > 200ms? scale_service api value=2
  • spike_warning? scale_service api value=3 NOW
  • queue_size > 3000? clear_queue queue
  • db_connections > 150? scale_service db value=2
  • cache_hit_rate < 0.5? adjust_cache cache
  • latency < 80ms and api replicas > 3? scale_service api value=-1

Incident fix map:
  service_crash → restart_service api
  db_overload → scale_service db value=2
  queue_flood → clear_queue queue
  cache_invalidation → adjust_cache cache
  auth_degraded → restart_service auth

Respond with ONE JSON object only. No markdown. No explanation.
```

**Fallback**: If LLM quota exhausted, switches to heuristic policy.

---

## 📈 Configuration

Edit `config/env_config.yaml` to tune simulation parameters:

```yaml
environment:
  name: infra-agent-env-v2
  version: 2.0.0

sla:
  latency_ms: 200              # SLA threshold
  p99_multiplier: 1.5

services:
  names: [api, auth, db, cache, queue]
  initial_replicas:
    api: 3
    auth: 2
    db: 2
    cache: 2
    queue: 2
  max_replicas: 10
  min_replicas: 1

tasks:
  task1_incident_recovery:
    max_steps: 100
    incident_step: 1
  task2_predictive_scaling:
    max_steps: 150
    incident_step: 50
  task3_root_cause:
    max_steps: 200
    incident_step: 35
    cascade_step: 60
```

---

## 🧪 Example Agent Implementation

### Random Agent (Baseline)
```python
from agents.random_agent import RandomAgent
from env.infra_env import InfraEnv

env = InfraEnv(task_id="task1_incident_recovery")
agent = RandomAgent(seed=42)

obs, info = env.reset()
done = False
total_reward = 0

while not done:
    action = agent.act(obs)
    step_result = env.step(action)
    obs = step_result.observation
    reward = step_result.reward
    done = step_result.done
    total_reward += reward

print(f"Episode finished. Total reward: {total_reward:.3f}")
```

### Custom LLM Agent
```python
from openai import OpenAI
from env.infra_env import InfraEnv
import json

client = OpenAI()
env = InfraEnv(task_id="task2_predictive_scaling")
obs, info = env.reset()

for step in range(150):
    # Build prompt
    prompt = f"Current state:\n{obs.get('summary')}\n\nWhat action?"
    
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.3
    )
    
    action_json = json.loads(response.choices[0].message.content)
    result = env.step(action_json)
    obs = result.observation
    
    if result.done:
        break
```

---

## 📊 Evaluation

Run the graders to benchmark agent performance:

```bash
# Single task evaluation
python graders/grader1.py --agent random --task task1_incident_recovery

# Full suite evaluation
python graders/grader1.py --agent your_agent
python graders/grader2.py --agent your_agent
python graders/grader3.py --agent your_agent
```

**Metrics**:
- **Completion Rate**: % episodes where agent reaches max_steps
- **SLA Maintenance**: % steps with latency < 200ms
- **Mean Reward**: Average episode reward
- **Incident Recovery Time**: Steps to resolve incident

---

## 🐳 Docker Deployment

Build and run the environment as a containerized service:

```bash
# Build image
docker build -t infra-agent-env:2.0 .

# Run container
docker run \
  -p 7860:7860 \
  -e HF_TOKEN="your-token" \
  -e TASK_ID="task1_incident_recovery" \
  infra-agent-env:2.0

# Health check
curl http://localhost:7860/health
```

---

## 🔬 Testing

Run the test suite:

```bash
pytest tests/ -v

# Specific test
pytest tests/test_env.py::test_reset -v

# With coverage
pytest tests/ --cov=env --cov=tasks
```

---

## 📚 Project Structure

| Module | Purpose |
|--------|---------|
| `env/` | Core RL environment (OpenEnv spec compliant) |
| `tasks/` | Task specifications & descriptions |
| `agents/` | Reference agent implementations |
| `graders/` | Evaluation & scoring logic |
| `utils/` | Utilities (summaries, rewards, alerts) |
| `config/` | YAML configuration files |
| `server/` | FastAPI application wrapper |
| `scripts/` | Utility shell scripts |
| `tests/` | Unit tests |
| `dashboard/` | Real-time monitoring UI |

---

## 🔧 Development

### Installing in editable mode
```bash
pip install -e .
```

### Running with auto-reload
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 7860
```

### Environment variables
```bash
export TASK_ID="task1_incident_recovery"          # Default task
export ENV_BASE_URL="http://localhost:7860"       # Environment server
export API_BASE_URL="https://router.huggingface.co/v1"  # LLM API
export MODEL_NAME="Qwen/Qwen2.5-72B-Instruct"     # LLM model
export HF_TOKEN="your-token"                       # HuggingFace token
```

---

## 📝 License

MIT License — See LICENSE file for details

---

## 🤝 Contributing

Contributions welcome! Areas for enhancement:
- [ ] Additional task types (multi-region, fault tolerance)
- [ ] More sophisticated simulators
- [ ] Benchmarks against state-of-the-art SRE policies
- [ ] Support for custom incidents & scenarios
- [ ] Integration with real monitoring systems (Prometheus, Grafana)

---

## 📞 Support

- **Issues**: Open a GitHub issue with reproduction steps
- **Documentation**: See docstrings in source code
- **Questions**: Check `tests/` and `agents/` for usage examples

---

**Built for autonomous SRE training. Powered by RL + LLMs. OpenEnv compliant.**