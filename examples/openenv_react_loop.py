"""Minimal OpenEnv ReAct-style DungeonGrid loop."""

from dungeongrid import DungeonGridEnvironment, dungeongrid_rules


def main() -> None:
    env = DungeonGridEnvironment()
    obs = env.reset(quest_id="lantern_crypt", num_heroes=1, seed=1)
    print(obs.text)
    print("\nRules: movement")
    print(dungeongrid_rules("movement"))

    result = env.act_plan(
        intent="Try to scout east, then leave a party note.",
        actions=[
            {"type": "move", "direction": "east"},
            {
                "type": "message",
                "target": "party",
                "payload": {"text": "I am scouting the east side first."},
            },
        ],
    )
    print("\nExecuted:", result.executed_actions)
    print("Skipped:", result.skipped_actions)
    print("Reveal:", result.reveal_reason)
    print("\nNext observation:")
    print(result.observation.text)


if __name__ == "__main__":
    main()
