"""Trace helpers."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def stable_hash(data: Any) -> str:
    payload = json.dumps(data, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def trace_record(
    *,
    turn_id: int,
    round_num: int,
    phase: str,
    agent_id: str,
    observation: dict[str, Any],
    action: dict[str, Any],
    state_before: dict[str, Any],
    state_after: dict[str, Any],
    narration: str,
    reward: float,
    violations: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "turn_id": turn_id,
        "round": round_num,
        "phase": phase,
        "agent_id": agent_id,
        "observation_hash": stable_hash(observation),
        "action": action,
        "state_before_hash": stable_hash(state_before),
        "state_after_hash": stable_hash(state_after),
        "narration": narration,
        "reward": reward,
        "violations": violations or [],
    }
