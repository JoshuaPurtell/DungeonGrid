"""Rollout and evaluation helpers."""

from __future__ import annotations

from typing import Any

from .baselines import AchievementScoutPolicy, ScriptedWardenPolicy
from .env import DungeonGridEnvironment
from .models import DungeonGridAction, model_to_dict


def run_episode(
    env: DungeonGridEnvironment,
    hero_policy: Any | None = None,
    warden_policy: Any | None = None,
    max_steps: int = 200,
    quest_id: str = "lantern_crypt",
    num_heroes: int = 1,
    seed: int | None = None,
) -> dict[str, Any]:
    """Run a policy-controlled episode and return trace + metrics."""
    if env.state is None:
        env.reset(quest_id=quest_id, num_heroes=num_heroes, seed=seed)
    hero_policy = hero_policy or AchievementScoutPolicy(seed=0)
    warden_policy = warden_policy or ScriptedWardenPolicy()
    steps = 0
    while not env.state.done and steps < max_steps:  # type: ignore[union-attr]
        active = env.state.active_agent()  # type: ignore[union-attr]
        obs = env.observe(active)
        obs_dict = model_to_dict(obs)
        obs_dict["legal_actions"] = env._legal_actions(active)
        action = warden_policy.act(obs_dict) if active == "warden" else hero_policy.act(obs_dict)
        env.step(DungeonGridAction(agent_id=active, **action))
        steps += 1
    result = env.export_trace()
    result["transcript"] = env.export_transcript()
    result["steps"] = steps
    return result


def summarize_achievement_frequencies(rollouts: list[dict[str, Any]]) -> dict[str, Any]:
    """Summarize unique achievement coverage across rollout artifacts."""
    total = len(rollouts)
    counts: dict[str, int] = {}
    rewards: dict[str, float] = {}
    by_quest: dict[str, dict[str, int]] = {}
    for rollout in rollouts:
        quest_id = str(rollout.get("quest_id") or rollout.get("transcript", {}).get("quest_id") or "unknown")
        metrics = rollout.get("metrics") or rollout.get("transcript", {}).get("metrics", {})
        achievements = metrics.get("achievements_unlocked") or [
            event.get("id") for event in rollout.get("transcript", {}).get("achievements", [])
        ]
        seen = {str(achievement_id) for achievement_id in achievements if achievement_id}
        by_quest.setdefault(quest_id, {})
        for achievement_id in seen:
            counts[achievement_id] = counts.get(achievement_id, 0) + 1
            by_quest[quest_id][achievement_id] = by_quest[quest_id].get(achievement_id, 0) + 1
        for event in rollout.get("transcript", {}).get("achievements", []):
            achievement_id = event.get("id")
            if achievement_id:
                rewards[str(achievement_id)] = max(rewards.get(str(achievement_id), 0.0), float(event.get("reward", 0.0)))
    return {
        "episodes": total,
        "achievement_counts": dict(sorted(counts.items())),
        "achievement_frequencies": {
            achievement_id: count / max(1, total)
            for achievement_id, count in sorted(counts.items())
        },
        "achievement_rewards": dict(sorted(rewards.items())),
        "by_quest": {
            quest_id: {
                achievement_id: count / max(1, len([r for r in rollouts if (r.get("quest_id") or r.get("transcript", {}).get("quest_id")) == quest_id]))
                for achievement_id, count in sorted(quest_counts.items())
            }
            for quest_id, quest_counts in sorted(by_quest.items())
        },
    }
