"""Rollout and evaluation helpers."""

from __future__ import annotations

from typing import Any

from .baselines import GreedyHeroPolicy, ScriptedWardenPolicy
from .env import DungeonGridEnvironment
from .models import DungeonGridAction


def run_episode(
    env: DungeonGridEnvironment,
    hero_policy: Any | None = None,
    warden_policy: Any | None = None,
    max_steps: int = 200,
) -> dict[str, Any]:
    """Run a policy-controlled episode and return trace + metrics."""
    hero_policy = hero_policy or GreedyHeroPolicy(seed=0)
    warden_policy = warden_policy or ScriptedWardenPolicy()
    steps = 0
    while not env.state.done and steps < max_steps:  # type: ignore[union-attr]
        active = env.state.active_agent()  # type: ignore[union-attr]
        obs = env.observe(active)
        obs_dict = obs.model_dump() if hasattr(obs, "model_dump") else obs.dict()
        action = warden_policy.act(obs_dict) if active == "warden" else hero_policy.act(obs_dict)
        env.step(DungeonGridAction(agent_id=active, **action))
        steps += 1
    result = env.export_trace()
    result["steps"] = steps
    return result
