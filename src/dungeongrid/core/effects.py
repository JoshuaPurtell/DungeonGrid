"""Typed state-machine primitives and effects for DungeonGrid."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from .data import Pos


class Phase(StrEnum):
    HERO_TURN = "hero_turn"
    PLAN_RESOLUTION = "plan_resolution"
    REVEAL = "reveal"
    WARDEN_TURN = "warden_turn"
    CLEANUP = "cleanup"
    DONE = "done"


class Timing(StrEnum):
    IMMEDIATE = "immediate"
    BEFORE_EFFECT = "before_effect"
    AFTER_EFFECT = "after_effect"
    REACTION = "reaction"
    REVEAL = "reveal"
    END_OF_ACTION = "end_of_action"
    END_OF_TURN = "end_of_turn"
    WARDEN = "warden"
    CLEANUP = "cleanup"


@dataclass(slots=True)
class ValidationFailure:
    reason: str
    message: str
    action: dict[str, Any]
    agent_id: str


@dataclass(slots=True)
class Effect:
    timing: Timing = Timing.IMMEDIATE

    @property
    def kind(self) -> str:
        return type(self).__name__

    def payload(self) -> dict[str, Any]:
        return {"kind": self.kind, "timing": self.timing.value}


@dataclass(slots=True)
class PayAP(Effect):
    entity_id: str = ""
    action_type: str = ""
    amount: int = 0


@dataclass(slots=True)
class Move(Effect):
    entity_id: str = ""
    to: Pos = (0, 0)
    direction: str = ""


@dataclass(slots=True)
class Damage(Effect):
    source_id: str = ""
    target_id: str = ""
    amount: int = 0
    source: str = "damage"
    ranged: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class BossPhaseChange(Effect):
    monster_id: str = ""
    phase_id: str = ""
    message: str = ""
    payload_data: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class BossDefeated(Effect):
    monster_id: str = ""
    source_id: str = ""


@dataclass(slots=True)
class Heal(Effect):
    target_id: str = ""
    amount: int = 0
    source: str = "heal"


@dataclass(slots=True)
class DrawCard(Effect):
    actor_id: str = ""
    deck_id: str = ""
    source_id: str = ""
    source_name: str = ""


@dataclass(slots=True)
class ApplyStatus(Effect):
    target_id: str = ""
    status: str = ""
    source: str = "status"


@dataclass(slots=True)
class RemoveStatus(Effect):
    target_id: str = ""
    status: str = ""
    source: str = "status"


@dataclass(slots=True)
class RevealTrap(Effect):
    trap_id: str = ""
    disarm: bool = False


@dataclass(slots=True)
class RevealSecretDoor(Effect):
    door_id: str = ""


@dataclass(slots=True)
class OpenDoor(Effect):
    actor_id: str = ""
    door_id: str = ""


@dataclass(slots=True)
class SpawnMonster(Effect):
    monster_id: str = ""
    role: str = "skitterling"
    pos: Pos | None = None
    activation: str = "engaged"
    status: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SpawnMonsterNear(Effect):
    monster_id: str = ""
    role: str = "skitterling"
    anchor_id: str = ""
    fallback_pos: Pos | None = None
    activation: str = "engaged"
    status: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ActivateMonster(Effect):
    monster_id: str = ""
    reason: str = "effect"


@dataclass(slots=True)
class SetFlag(Effect):
    key: str = ""
    value: Any = True


@dataclass(slots=True)
class IncrementCounter(Effect):
    key: str = ""
    amount: int = 1
    default: int = 0


@dataclass(slots=True)
class ModifyAlert(Effect):
    amount: int = 0


@dataclass(slots=True)
class AddInventory(Effect):
    target_id: str = ""
    item_id: str = ""


@dataclass(slots=True)
class RemoveInventory(Effect):
    target_id: str = ""
    item_id: str = ""


@dataclass(slots=True)
class TransferItem(Effect):
    source_id: str = ""
    target_id: str = ""
    item_id: str = ""


@dataclass(slots=True)
class EquipItem(Effect):
    actor_id: str = ""
    item_id: str = ""


@dataclass(slots=True)
class EmitEvent(Effect):
    message: str = ""
    trace_kind: str | None = None
    payload_data: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class UnlockAchievement(Effect):
    achievement_id: str = ""
    title: str = ""
    reward: float = 0.0
    layer: str = "quest"
    description: str = ""


@dataclass(slots=True)
class AdvancePhase(Effect):
    target: Phase = Phase.CLEANUP


@dataclass(slots=True)
class MessageEffect(Effect):
    actor_id: str = ""
    target: str = "party"
    text: str = ""


@dataclass(slots=True)
class Guard(Effect):
    actor_id: str = ""


@dataclass(slots=True)
class DisarmTrap(Effect):
    actor_id: str = ""
    trap_id: str = ""


@dataclass(slots=True)
class OpenChest(Effect):
    actor_id: str = ""
    chest_id: str = ""


@dataclass(slots=True)
class SearchFurniture(Effect):
    actor_id: str = ""
    furniture_id: str = ""
    category: str = "furniture"
    via_interact: bool = False


@dataclass(slots=True)
class DamageFurniture(Effect):
    actor_id: str = ""
    furniture_id: str = ""
    amount: int = 0


@dataclass(slots=True)
class ObjectiveTake(Effect):
    actor_id: str = ""


@dataclass(slots=True)
class ObjectiveEscape(Effect):
    actor_id: str = ""


@dataclass(slots=True)
class SearchArea(Effect):
    actor_id: str = ""
    category: str = "traps"
    pos: Pos | None = None


@dataclass(slots=True)
class UseItem(Effect):
    actor_id: str = ""
    item_id: str = ""


@dataclass(slots=True)
class AttackRoll(Effect):
    attacker_id: str = ""
    target_id: str = ""
    ranged: bool = False


@dataclass(slots=True)
class CastSpell(Effect):
    caster_id: str = ""
    spell: str = ""
    target_id: str = ""


@dataclass(slots=True)
class MonsterAct(Effect):
    monster_id: str = ""


@dataclass(slots=True)
class EndTurn(Effect):
    actor_id: str = ""
