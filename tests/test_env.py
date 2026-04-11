"""tests/test_env.py — Core environment tests."""
import pytest
from env.infra_env import InfraEnv
from env.schemas import InfraAction, ActionType

TASKS = [
    "task1_incident_recovery",
    "task2_predictive_scaling",
    "task3_root_cause",
]


@pytest.mark.parametrize("task_id", TASKS)
def test_reset_returns_observation(task_id):
    env = InfraEnv(task_id=task_id)
    result = env.reset()
    assert result.observation is not None
    assert result.observation.time_step == 0
    assert result.observation.avg_latency_ms >= 0


@pytest.mark.parametrize("task_id", TASKS)
def test_step_returns_valid_reward(task_id):
    env = InfraEnv(task_id=task_id)
    env.reset()
    action = InfraAction(action_type=ActionType.DO_NOTHING)
    result = env.step(action)
    assert 0.0 <= result.reward <= 1.0
    assert result.observation is not None
    assert isinstance(result.done, bool)


@pytest.mark.parametrize("task_id", TASKS)
def test_state_returns_full_state(task_id):
    env = InfraEnv(task_id=task_id)
    env.reset()
    state = env.state()
    assert state.task_id == task_id
    assert state.time_step == 0


@pytest.mark.parametrize("task_id", TASKS)
def test_episode_terminates(task_id):
    env = InfraEnv(task_id=task_id)
    env.reset()
    done = False
    steps = 0
    while not done and steps < 250:
        result = env.step(InfraAction(action_type=ActionType.DO_NOTHING))
        done = result.done
        steps += 1
    assert done, f"Episode did not terminate for {task_id}"


def test_scale_service_increases_replicas():
    env = InfraEnv(task_id="task1_incident_recovery")
    env.reset()
    before = env.ms_sim.replicas["api"]
    env.step(InfraAction(action_type=ActionType.SCALE_SERVICE, service="api", value=2))
    after = env.ms_sim.replicas["api"]
    assert after == min(before + 2, 10)


def test_reward_always_in_range():
    env = InfraEnv(task_id="task1_incident_recovery")
    env.reset()
    for _ in range(30):
        result = env.step(InfraAction(action_type=ActionType.SCALE_SERVICE, service="api", value=1))
        assert 0.0 <= result.reward <= 1.0
        if result.done:
            break


def test_reset_after_done():
    env = InfraEnv(task_id="task1_incident_recovery")
    env.reset()
    for _ in range(110):
        r = env.step(InfraAction(action_type=ActionType.DO_NOTHING))
        if r.done:
            break
    result = env.reset()
    assert result.observation.time_step == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
