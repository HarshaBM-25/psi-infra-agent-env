"""agents/random_agent.py — Random baseline. Establishes floor score."""
import random
from env.schemas import InfraAction, ActionType

SERVICES = ["api", "auth", "db", "cache", "queue"]

class RandomAgent:
    def __init__(self, seed: int = 0):
        self._rng = random.Random(seed)

    def act(self, obs: dict) -> InfraAction:
        action = self._rng.choice(list(ActionType))
        service = self._rng.choice(SERVICES)
        value = self._rng.randint(1, 2)
        return InfraAction(action_type=action, service=service, value=value)
