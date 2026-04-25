"""Run a tiny scripted-policy DungeonGrid benchmark smoke."""

from __future__ import annotations

import argparse
import json
import time
from typing import Any

from dungeongrid import DungeonGridEnvironment


def choose_action(env: DungeonGridEnvironment, agent_id: str) -> dict[str, Any]:
    legal = env._legal_actions(agent_id)
    for action_type in (
        "attack_melee",
        "attack_ranged",
        "cast",
        "interact",
        "open_door",
        "search_treasure",
        "search_furniture",
        "inspect_room",
        "move",
        "warden_auto",
        "end_turn",
    ):
        for action in legal:
            if action.get("type") == action_type:
                return action
    return {"type": "end_turn"}


def run_episode(
    quest_id: str, *, num_heroes: int, seed: int, max_steps: int, ruleset: str | None
) -> dict[str, Any]:
    env = DungeonGridEnvironment()
    env.reset(quest_id=quest_id, num_heroes=num_heroes, seed=seed, ruleset=ruleset)
    reward = 0.0
    start = time.perf_counter()
    steps = 0
    for step_index in range(1, max_steps + 1):
        steps = step_index
        agent_id = env.state.active_agent()
        step = env.step(choose_action(env, agent_id), agent_id=agent_id)
        reward += step.reward
        if step.done:
            break
    elapsed = time.perf_counter() - start
    metrics = env.export_transcript()["metrics"]
    return {
        "quest_id": quest_id,
        "seed": seed,
        "num_heroes": num_heroes,
        "ruleset": ruleset or "default",
        "steps": steps,
        "total_reward": round(reward, 4),
        "wall_clock_seconds": round(elapsed, 4),
        "steps_per_second": round(steps / max(elapsed, 1e-9), 2),
        **metrics,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--suite", choices=["solo20", "coop20", "lite20"], default="solo20")
    parser.add_argument("--seeds", type=int, default=1)
    parser.add_argument("--max-steps", type=int, default=80)
    parser.add_argument("--classic-dynamic", action="store_true")
    args = parser.parse_args()

    env = DungeonGridEnvironment()
    quest_ids = env.grid.available_quests()
    if args.suite == "lite20":
        quest_ids = [quest_id for quest_id in quest_ids if quest_id.endswith("_lite")]
        num_heroes = 2
    elif args.suite == "coop20":
        quest_ids = [quest_id for quest_id in quest_ids if not quest_id.endswith("_lite")]
        num_heroes = 2
    else:
        quest_ids = [quest_id for quest_id in quest_ids if not quest_id.endswith("_lite")]
        num_heroes = 1

    rows = [
        run_episode(
            quest_id,
            num_heroes=num_heroes,
            seed=seed,
            max_steps=args.max_steps,
            ruleset="classic_dynamic" if args.classic_dynamic else None,
        )
        for quest_id in quest_ids
        for seed in range(args.seeds)
    ]
    print(json.dumps({"suite": args.suite, "episodes": rows}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
