"""Lightweight DungeonGrid content validation CLI."""

from __future__ import annotations

import argparse
import json
from typing import Any

from .env import DungeonGridEnvironment


def validate_dungeons(*, include_classic_dynamic: bool = True) -> dict[str, Any]:
    """Validate bundled dungeons can reset and expose public observations safely."""
    env = DungeonGridEnvironment()
    quest_ids = env.grid.available_quests()
    results: list[dict[str, Any]] = []
    rulesets: list[str | None] = [None, "classic_dynamic"] if include_classic_dynamic else [None]
    for quest_id in quest_ids:
        for ruleset in rulesets:
            for num_heroes in (1, 2, 3, 4):
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate bundled DungeonGrid dungeons.")
    parser.add_argument(
        "--default-only",
        action="store_true",
        help="Skip classic_dynamic validation.",
    )
    args = parser.parse_args()
    result = validate_dungeons(include_classic_dynamic=not args.default_only)
    print(json.dumps(result, indent=2, sort_keys=True))
    if not result["ok"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
