"""Measure communication premium/penalty on tiered DungeonGrid quests.

Runs the same deterministic baseline on a quest set with communication enabled
and disabled, then reports score and success-rate deltas.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import statistics
import time
from dataclasses import dataclass
from typing import Any

from dungeongrid import DungeonGridEnvironment
from dungeongrid.baselines import GreedyHeroPolicy, ScriptedWardenPolicy
from dungeongrid.core.grid_engine import GridEngine


COMMUNICATION_ON = {"mode": "pure_decentralized"}
COMMUNICATION_OFF = {"mode": "no_message"}


@dataclass(frozen=True)
class EpisodeSpec:
    quest_id: str
    seed: int
    condition: str
    communication_protocol: dict[str, Any]
    max_steps: int


def choose_policy_action(
    policy: GreedyHeroPolicy,
    observation: dict[str, Any],
    *,
    allow_messages: bool,
    message_sent: bool,
) -> dict[str, Any]:
    """Choose an action while making no-message runs protocol-aware."""

    legal = list(observation.get("legal_actions", []))
    if allow_messages and not message_sent:
        for action in legal:
            if action.get("type") == "message" and action.get("target") == "party":
                return {
                    "type": "message",
                    "target": "party",
                    "payload": {
                        "text": "I am sharing role, route, and counterplay progress with the party."
                    },
                }
    if not allow_messages or message_sent:
        legal = [action for action in legal if action.get("type") != "message"]
    observation = {**observation, "legal_actions": legal or [{"type": "end_turn"}]}
    return policy.act(observation)


def run_episode(spec: EpisodeSpec) -> dict[str, Any]:
    env = DungeonGridEnvironment()
    env.reset(
        quest_id=spec.quest_id,
        num_heroes=2,
        seed=spec.seed,
        communication_protocol=spec.communication_protocol,
    )
    hero_policy = GreedyHeroPolicy(seed=spec.seed)
    warden_policy = ScriptedWardenPolicy()
    allow_messages = spec.communication_protocol.get("mode") != "no_message"
    message_sent = False
    total_reward = 0.0
    steps = 0
    started = time.perf_counter()

    while env.state is not None and not env.state.done and steps < spec.max_steps:
        active = env.state.active_agent()
        obs = env.observe(active).model_dump()
        obs["legal_actions"] = env._legal_actions(active)
        if active == "warden":
            action = warden_policy.act(obs)
        else:
            action = choose_policy_action(
                hero_policy,
                obs,
                allow_messages=allow_messages,
                message_sent=message_sent,
            )
        step = env.step(action, agent_id=active)
        if active != "warden" and action.get("type") == "message" and not step.info.get("invalid"):
            message_sent = True
        total_reward += step.reward
        steps += 1

    elapsed = time.perf_counter() - started
    transcript = env.export_transcript()
    metrics = transcript["metrics"]
    message_metrics = metrics.get("message_metrics", {})
    return {
        "quest_id": env.state.quest_id if env.state is not None else spec.quest_id,
        "seed": spec.seed,
        "condition": spec.condition,
        "communication_protocol": spec.communication_protocol["mode"],
        "steps": steps,
        "total_reward": round(total_reward, 4),
        "success": bool(metrics.get("success")),
        "winner": metrics.get("winner"),
        "achievement_count": metrics.get("achievement_count", 0),
        "quest_achievement_count": metrics.get("quest_achievement_count", 0),
        "messages_attempted": int(message_metrics.get("messages_attempted", 0) or 0),
        "messages_delivered": int(message_metrics.get("messages_delivered", 0) or 0),
        "messages_rejected": int(message_metrics.get("messages_rejected", 0) or 0),
        "wall_clock_seconds": round(elapsed, 4),
    }


def summarize_rows(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_condition: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_condition.setdefault(str(row["condition"]), []).append(row)

    condition_summary: dict[str, dict[str, Any]] = {}
    for condition, condition_rows in sorted(by_condition.items()):
        rewards = [float(row["total_reward"]) for row in condition_rows]
        condition_summary[condition] = {
            "episodes": len(condition_rows),
            "successes": sum(1 for row in condition_rows if row["success"]),
            "success_rate": round(
                sum(1 for row in condition_rows if row["success"]) / max(1, len(condition_rows)),
                4,
            ),
            "mean_total_reward": round(statistics.fmean(rewards), 4) if rewards else 0.0,
            "median_total_reward": round(statistics.median(rewards), 4) if rewards else 0.0,
            "messages_delivered": sum(int(row["messages_delivered"]) for row in condition_rows),
            "messages_rejected": sum(int(row["messages_rejected"]) for row in condition_rows),
        }

    pairs: list[dict[str, Any]] = []
    keyed: dict[tuple[str, int], dict[str, dict[str, Any]]] = {}
    for row in rows:
        keyed.setdefault((str(row["quest_id"]), int(row["seed"])), {})[str(row["condition"])] = row
    for (quest_id, seed), pair in sorted(keyed.items()):
        with_comm = pair.get("communication")
        no_comm = pair.get("no_communication")
        if with_comm is None or no_comm is None:
            continue
        pairs.append(
            {
                "quest_id": quest_id,
                "seed": seed,
                "score_delta": round(
                    float(with_comm["total_reward"]) - float(no_comm["total_reward"]), 4
                ),
                "success_delta": int(bool(with_comm["success"])) - int(bool(no_comm["success"])),
                "communication_score": with_comm["total_reward"],
                "no_communication_score": no_comm["total_reward"],
                "communication_success": with_comm["success"],
                "no_communication_success": no_comm["success"],
            }
        )

    score_deltas = [float(pair["score_delta"]) for pair in pairs]
    success_deltas = [int(pair["success_delta"]) for pair in pairs]
    return {
        "conditions": condition_summary,
        "communication_premium": {
            "paired_episodes": len(pairs),
            "mean_score_delta": round(statistics.fmean(score_deltas), 4) if score_deltas else 0.0,
            "median_score_delta": round(statistics.median(score_deltas), 4) if score_deltas else 0.0,
            "success_rate_delta": round(statistics.fmean(success_deltas), 4)
            if success_deltas
            else 0.0,
            "interpretation": "positive means communication premium; negative means communication penalty",
        },
        "paired_results": pairs,
    }


def quest_ids_for_args(args: argparse.Namespace) -> list[str]:
    grid = GridEngine()
    if args.quest:
        return [args.quest]
    quests = [
        quest_id
        for quest_id in grid.available_tiered_quests()
        if quest_id.endswith(f":{args.tier}")
    ]
    if args.family:
        quests = [quest_id for quest_id in quests if quest_id == f"base:{args.family}:{args.tier}"]
    return sorted(quests)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tier", default="lite", choices=["pico", "lite", "medium", "heavy"])
    parser.add_argument("--quest", help="Explicit quest id such as base:lantern_crypt:lite")
    parser.add_argument("--family", help="Family name, e.g. lantern_crypt")
    parser.add_argument("--seeds", type=int, default=5)
    parser.add_argument("--seed-offset", type=int, default=0)
    parser.add_argument("--max-steps", type=int, default=120)
    parser.add_argument("--max-workers", type=int, default=8)
    parser.add_argument("--include-episodes", action="store_true")
    args = parser.parse_args()

    quest_ids = quest_ids_for_args(args)
    specs = [
        EpisodeSpec(
            quest_id=quest_id,
            seed=args.seed_offset + seed,
            condition=condition,
            communication_protocol=protocol,
            max_steps=args.max_steps,
        )
        for quest_id in quest_ids
        for seed in range(args.seeds)
        for condition, protocol in (
            ("communication", COMMUNICATION_ON),
            ("no_communication", COMMUNICATION_OFF),
        )
    ]

    with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.max_workers)) as pool:
        rows = list(pool.map(run_episode, specs))

    payload = {
        "suite": f"{args.tier}_communication_premium",
        "tier": args.tier,
        "quest_count": len(quest_ids),
        "seeds": args.seeds,
        "episodes": len(rows),
        "summary": summarize_rows(rows),
    }
    if args.include_episodes:
        payload["episode_results"] = sorted(
            rows,
            key=lambda row: (row["quest_id"], row["seed"], row["condition"]),
        )
    print(json.dumps(payload, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
