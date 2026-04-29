"""Run a bounded DungeonGrid smoke with an OpenAI model and dungeongrid_act.

This is a diagnostic harness, not a benchmark suite. It uses the same
tool-shaped action envelope described in observations, then validates every
submitted action against the environment's current legal actions before calling
act_plan.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path
from typing import Any

from dungeongrid import DungeonGridEnvironment


def load_env_file(path: str | None) -> None:
    if not path:
        return
    env_path = Path(path).expanduser()
    if not env_path.is_file():
        raise FileNotFoundError(f"env file not found: {env_path}")
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key, value.strip().strip('"').strip("'"))


def action_key(action: dict[str, Any]) -> str:
    return json.dumps(action, sort_keys=True, separators=(",", ":"))


def normalize_model_action(action: Any, legal: list[dict[str, Any]]) -> dict[str, Any] | None:
    if not isinstance(action, dict):
        return None
    legal_by_key = {action_key(item): item for item in legal}
    key = action_key(action)
    if key in legal_by_key:
        return legal_by_key[key]
    if action.get("type") == "move" and action.get("direction"):
        matches = [
            item
            for item in legal
            if item.get("type") == "move" and item.get("direction") == action.get("direction")
        ]
        if len(matches) == 1:
            return matches[0]
    return None


def fallback_action(legal: list[dict[str, Any]]) -> dict[str, Any]:
    for action_type in (
        "interact",
        "open_door",
        "attack_melee",
        "attack_ranged",
        "disarm",
        "move",
        "warden_auto",
        "guard",
        "end_turn",
    ):
        for action in legal:
            if action.get("type") == action_type:
                return action
    return legal[0] if legal else {"type": "end_turn"}


def tool_args_from_response(response: Any) -> tuple[dict[str, Any] | None, str]:
    message = response.choices[0].message
    tool_calls = message.tool_calls or []
    for call in tool_calls:
        if call.function.name != "dungeongrid_act":
            continue
        try:
            return json.loads(call.function.arguments), call.function.arguments
        except json.JSONDecodeError:
            return None, call.function.arguments
    text = message.content or ""
    match = re.search(r"\{.*\}", text, flags=re.S)
    if not match:
        return None, text
    try:
        raw = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None, text
    if isinstance(raw, dict) and "dungeongrid_act" in raw:
        raw = raw["dungeongrid_act"]
    return raw if isinstance(raw, dict) else None, text


def choose_model_plan(client: Any, args: argparse.Namespace, env: DungeonGridEnvironment) -> tuple[str, list[dict[str, Any]], dict[str, Any]]:
    active = env.state.active_agent()
    legal = env._legal_actions(active)
    if active == "warden":
        return "deterministic_warden", [fallback_action(legal)], {"raw": "local_warden"}

    obs = env.observe(active)
    response = client.chat.completions.create(
        model=args.model,
        temperature=args.temperature,
        max_tokens=args.max_tokens,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are playing DungeonGrid. Use the dungeongrid_act tool exactly once. "
                    "Choose exactly one action_index from legal_actions. Prefer objective "
                    "progress: move toward visible doors/objectives, open adjacent doors, pick up "
                    "the objective, then escape. Avoid repeating the last position unless it opens "
                    "or reveals progress."
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "active_agent": active,
                        "observation": obs.text,
                        "symbolic": obs.symbolic,
                        "legal_actions": legal,
                    },
                    separators=(",", ":"),
                ),
            },
        ],
        tools=[
            {
                "type": "function",
                "function": {
                    "name": "dungeongrid_act",
                    "description": "Submit a short DungeonGrid action plan by selecting indexes from the provided legal_actions array.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "intent": {"type": "string"},
                            "action_indexes": {
                                "type": "array",
                                "minItems": 1,
                                "maxItems": args.max_plan_actions,
                                "items": {"type": "integer", "minimum": 0},
                            },
                        },
                        "required": ["intent", "action_indexes"],
                        "additionalProperties": False,
                    },
                    "strict": True,
                },
            }
        ],
        tool_choice={"type": "function", "function": {"name": "dungeongrid_act"}},
    )
    tool_args, raw = tool_args_from_response(response)
    submitted = tool_args.get("actions", []) if isinstance(tool_args, dict) else []
    action_indexes = tool_args.get("action_indexes", []) if isinstance(tool_args, dict) else []
    indexed_actions = [
        legal[index]
        for index in action_indexes
        if isinstance(index, int) and 0 <= index < len(legal)
    ]
    normalized = [
        normalized
        for action in submitted
        for normalized in [normalize_model_action(action, legal)]
        if normalized is not None
    ]
    if indexed_actions:
        normalized = indexed_actions
    fallback_used = False
    if not normalized:
        normalized = [fallback_action(legal)]
        fallback_used = True
    intent = str(tool_args.get("intent", "model_plan") if isinstance(tool_args, dict) else "model_plan")
    return intent, normalized[: args.max_plan_actions], {
        "raw": raw,
        "submitted": submitted,
        "fallback_used": fallback_used,
    }


def run(args: argparse.Namespace) -> dict[str, Any]:
    load_env_file(args.env_file)
    if not os.environ.get("OPENAI_API_KEY"):
        raise RuntimeError("OPENAI_API_KEY is not set")
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    env = DungeonGridEnvironment()
    env.reset(
        quest_id=args.quest_id,
        num_heroes=args.num_heroes,
        seed=args.seed,
        ruleset="classic_dynamic" if args.classic_dynamic else None,
    )
    transcript: list[dict[str, Any]] = []
    total_reward = 0.0
    for turn in range(1, args.max_turns + 1):
        if env.state.done:
            break
        active = env.state.active_agent()
        intent, actions, model_info = choose_model_plan(client, args, env)
        result = env.act_plan(actions, intent=intent, agent_id=active)
        total_reward += result.reward
        row = {
            "turn": turn,
            "agent_id": active,
            "intent": intent,
            "actions": actions,
            "executed": result.executed_actions,
            "skipped": result.skipped_actions,
            "unused": result.unused_actions,
            "reward": round(result.reward, 4),
            "done": result.done,
            "winner": env.state.winner,
            "reveal_reason": result.reveal_reason,
            "model": model_info,
        }
        transcript.append(row)
        print(json.dumps({k: row[k] for k in ("turn", "agent_id", "actions", "reward", "done", "winner", "reveal_reason")}, sort_keys=True))
    summary = {
        "model": args.model,
        "quest_id": env.state.quest_id,
        "num_heroes": args.num_heroes,
        "seed": args.seed,
        "ruleset": "classic_dynamic" if args.classic_dynamic else "default",
        "turns": len(transcript),
        "done": env.state.done,
        "winner": env.state.winner,
        "total_reward": round(total_reward, 4),
        "metrics": env.export_transcript()["metrics"],
    }
    output = {"summary": summary, "transcript": transcript, "export": env.export_transcript()}
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{args.quest_id.replace(':', '_')}_{args.model}_{int(time.time())}.json"
    out_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    print("SUMMARY", json.dumps(summary, sort_keys=True))
    print("TRANSCRIPT", out_path)
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quest-id", default="goblin:ironroot_hold:lite")
    parser.add_argument("--num-heroes", type=int, default=2)
    parser.add_argument("--seed", type=int, default=41)
    parser.add_argument("--model", default="gpt-4.1-mini")
    parser.add_argument("--max-turns", type=int, default=20)
    parser.add_argument("--max-plan-actions", type=int, default=1)
    parser.add_argument("--max-tokens", type=int, default=300)
    parser.add_argument("--temperature", type=float, default=0.2)
    parser.add_argument("--classic-dynamic", action="store_true")
    parser.add_argument("--env-file")
    parser.add_argument("--out-dir", default=".out/openai_model_smoke")
    run(parser.parse_args())


if __name__ == "__main__":
    main()
