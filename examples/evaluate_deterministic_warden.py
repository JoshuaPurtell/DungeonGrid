"""Run a tiny classic_dynamic episode with bounded deterministic Warden pressure."""

from __future__ import annotations

import argparse
import json
from typing import Any

from dungeongrid import DeterministicWardenPolicy, DungeonGridEnvironment


def choose_hero_action(env: DungeonGridEnvironment, agent_id: str) -> dict[str, Any]:
    for action_type in (
        "interact",
        "open_door",
        "search_treasure",
        "search_furniture",
        "attack_melee",
        "move",
        "guard",
        "end_turn",
    ):
        for action in env._legal_actions(agent_id):
            if action.get("type") == action_type:
                return action
    return {"type": "end_turn"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quest-id", default="magistrate_gold")
    parser.add_argument("--num-heroes", type=int, default=2)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--max-steps", type=int, default=40)
    args = parser.parse_args()

    env = DungeonGridEnvironment()
    env.reset(
        quest_id=args.quest_id,
        num_heroes=args.num_heroes,
        seed=args.seed,
        ruleset="classic_dynamic",
    )
    warden = DeterministicWardenPolicy()
    total_reward = 0.0
    for _ in range(args.max_steps):
        agent_id = env.state.active_agent()
        if agent_id == "warden":
            action = warden.act(env.observe_warden())
        else:
            action = choose_hero_action(env, agent_id)
        step = env.step(action, agent_id=agent_id)
        total_reward += step.reward
        if step.done:
            break

    transcript = env.export_transcript()
    print(
        json.dumps(
            {
                "quest_id": args.quest_id,
                "ruleset": "classic_dynamic",
                "total_reward": round(total_reward, 4),
                "metrics": transcript["metrics"],
                "warden_turns": [
                    turn for turn in transcript["turns"] if turn.get("agent_id") == "warden"
                ],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
