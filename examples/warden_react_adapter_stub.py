"""Minimal Warden ReAct adapter stub without making model calls."""

from __future__ import annotations

import json
from typing import Any

from dungeongrid import DungeonGridEnvironment, WardenDecision, WardenReActAdapter


def planner_stub(observation: dict[str, Any]) -> WardenDecision:
    """Pretend this function is a model/tool-call planner."""

    for action in observation["legal_actions"]:
        if action["type"] == "warden_spend_dread":
            return WardenDecision(
                action=action,
                policy="example_react_stub",
                intent="use one bounded dread action to test the dungeon MARL axis",
                axis_pressure=str(observation.get("marl_axis")),
                fairness_check="selected only from legal Warden candidates",
            )
    return WardenDecision(
        action={"type": "warden_auto"},
        policy="example_react_stub",
        intent="advance revealed threats without extra pressure",
        axis_pressure=str(observation.get("marl_axis")),
        fairness_check="no dread candidate was available",
    )


def main() -> None:
    env = DungeonGridEnvironment()
    env.reset(quest_id="magistrate_gold", num_heroes=2, seed=2, ruleset="classic_dynamic")
    env.state.phase = "warden"
    env.state.dread = 1
    adapter = WardenReActAdapter(planner_stub, name="example_react_stub")
    observation = env.observe_warden()
    action = adapter.act(observation)
    print(json.dumps({"observation_keys": sorted(observation), "action": action}, indent=2))


if __name__ == "__main__":
    main()
