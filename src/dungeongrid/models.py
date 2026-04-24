"""Typed models for DungeonGrid's OpenEnv-style API."""

from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, Field


def model_to_dict(model: Any) -> dict[str, Any]:
    """Pydantic v1/v2 compatible conversion."""
    if hasattr(model, "model_dump"):
        return model.model_dump()
    if hasattr(model, "dict"):
        return model.dict()
    if isinstance(model, dict):
        return model
    raise TypeError(f"Cannot convert {type(model)!r} to dict")


class DungeonGridAction(BaseModel):
    """Single action submitted by an active hero or the Warden.

    Common examples:
      - {"agent_id": "hero_1", "type": "move", "direction": "east"}
      - {"agent_id": "hero_2", "type": "attack_melee", "target": "skitterling_1"}
      - {"agent_id": "hero_1", "type": "message", "target": "party", "payload": {"text": "Wizard scout east."}}
      - {"agent_id": "warden", "type": "warden_auto"}
    """

    agent_id: Optional[str] = None
    type: str = Field(..., description="Action type, e.g. move, open_door, attack_melee.")
    direction: Optional[str] = None
    target: Optional[Any] = None
    payload: dict[str, Any] = Field(default_factory=dict)


class DungeonGridObservation(BaseModel):
    """Natural-language and symbolic observation for a single agent."""

    agent_id: str
    active_agent: str
    round: int
    phase: str
    text: str
    visible_map: str
    symbolic: dict[str, Any]


class DungeonGridState(BaseModel):
    """Serialized server-side state."""

    data: dict[str, Any]


class DungeonGridStep(BaseModel):
    """Step result with Gym/OpenEnv-style fields."""

    observation: DungeonGridObservation
    reward: float
    done: bool
    info: dict[str, Any] = Field(default_factory=dict)


class DungeonGridPlanResult(BaseModel):
    """Result of executing one OpenEnv ReAct-style queued action plan."""

    intent: Optional[str] = None
    submitted_actions: list[dict[str, Any]]
    executed_actions: list[dict[str, Any]] = Field(default_factory=list)
    skipped_actions: list[dict[str, Any]] = Field(default_factory=list)
    unused_actions: list[dict[str, Any]] = Field(default_factory=list)
    reveal_stopped: bool = False
    reveal_reason: Optional[str] = None
    reward: float = 0.0
    done: bool = False
    observation: DungeonGridObservation
