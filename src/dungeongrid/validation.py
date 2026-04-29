"""Lightweight DungeonGrid content validation CLI."""

from __future__ import annotations

import argparse
import json
from typing import Any

from .env import DungeonGridEnvironment


def validate_dungeons(
    *,
    include_classic_dynamic: bool = True,
    include_tiered: bool = False,
    tiered_only: bool = False,
) -> dict[str, Any]:
    """Validate bundled dungeons can reset and expose public observations safely."""
    env = DungeonGridEnvironment()
    quest_ids = (
        env.grid.available_tiered_quests()
        if tiered_only
        else env.grid.available_quests(include_tiered=include_tiered)
    )
    results: list[dict[str, Any]] = []
    rulesets: list[str | None] = [None, "classic_dynamic"] if include_classic_dynamic else [None]
    for quest_id in quest_ids:
        for ruleset in rulesets:
            for num_heroes in _hero_counts_for_quest(env, quest_id):
                obs = env.reset(quest_id=quest_id, num_heroes=num_heroes, seed=0, ruleset=ruleset)
                public = env.public_state_json()
                results.append(
                    {
                        "quest_id": quest_id,
                        "ruleset": ruleset or "default",
                        "num_heroes": num_heroes,
                        "active_agent": obs.active_agent,
                        "ok": "legal_actions" not in public and "legal_actions" not in obs.symbolic,
                    }
                )
    failures = [row for row in results if not row["ok"]]
    return {
        "ok": not failures,
        "quest_count": len(quest_ids),
        "checks": len(results),
        "failures": failures,
    }


def _hero_counts_for_quest(env: DungeonGridEnvironment, quest_id: str) -> tuple[int, ...]:
    if _is_tiered_quest_id(quest_id):
        data = env.grid.load_quest_data(quest_id)
        intended = data.get("metadata", {}).get("intended_num_heroes")
        if intended:
            return (int(intended),)
    return (1, 2, 3, 4)


def _is_tiered_quest_id(quest_id: str) -> bool:
    parts = quest_id.split(":")
    return len(parts) == 3 and parts[2] in {"pico", "lite", "medium", "heavy"}


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate bundled DungeonGrid dungeons.")
    parser.add_argument(
        "--default-only",
        action="store_true",
        help="Skip classic_dynamic validation.",
    )
    parser.add_argument(
        "--include-tiered",
        action="store_true",
        help="Also validate tiered expansion quests.",
    )
    parser.add_argument(
        "--tiered-only",
        action="store_true",
        help="Validate only tiered expansion quests.",
    )
    args = parser.parse_args()
    result = validate_dungeons(
        include_classic_dynamic=not args.default_only,
        include_tiered=args.include_tiered,
        tiered_only=args.tiered_only,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
