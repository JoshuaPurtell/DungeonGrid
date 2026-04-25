"""Reusable typed hook helpers for DungeonGrid dungeon modules."""

from __future__ import annotations

from collections.abc import Iterable

from dungeongrid.core.effects import (
    Effect,
    EmitEvent,
    IncrementCounter,
    ModifyAlert,
    SetFlag,
    SpawnMonster,
    UnlockAchievement,
)


def payload(ctx) -> dict:
    data = ctx.info.get("trigger_payload")
    return data if isinstance(data, dict) else {}


def objective_flag(flag: str, *, extra: Iterable[Effect] = ()) -> callable:
    def handler(ctx) -> list[Effect]:
        if payload(ctx).get("objective_id") != ctx.state.objective.id:
            return []
        return [SetFlag(key=flag, value=True), *list(extra)]

    return handler


def clue_flags(targets: set[str], read_flag: str, before_flag: str | None = None) -> callable:
    def handler(ctx) -> list[Effect]:
        if payload(ctx).get("furniture_id") not in targets:
            return []
        effects: list[Effect] = [SetFlag(key=read_flag, value=True)]
        if before_flag and ctx.state.objective.carrier is None:
            effects.append(SetFlag(key=before_flag, value=True))
        return effects

    return handler


def message_after(flag: str, set_flag: str, achievement: dict | None = None) -> callable:
    def handler(ctx) -> list[Effect]:
        if not ctx.state.scripts.get(flag):
            return []
        effects: list[Effect] = [SetFlag(key=set_flag, value=True)]
        if achievement:
            effects.append(achievement_effect(**achievement))
        return effects

    return handler


def guard_after(flag: str, set_flag: str, achievement: dict | None = None) -> callable:
    def handler(ctx) -> list[Effect]:
        if not ctx.state.scripts.get(flag):
            return []
        effects: list[Effect] = [SetFlag(key=set_flag, value=True)]
        if achievement:
            effects.append(achievement_effect(**achievement))
        return effects

    return handler


def attack_after(
    flag: str, set_flag: str, *, ranged: bool | None = None, achievement: dict | None = None
) -> callable:
    def handler(ctx) -> list[Effect]:
        if not ctx.state.scripts.get(flag):
            return []
        effect = payload(ctx).get("effect", {})
        if ranged is not None and bool(effect.get("ranged")) != ranged:
            return []
        effects: list[Effect] = [SetFlag(key=set_flag, value=True)]
        if achievement:
            effects.append(achievement_effect(**achievement))
        return effects

    return handler


def achievement_effect(
    *,
    id: str,
    title: str,
    reward: float,
    description: str,
    layer: str = "quest",
) -> UnlockAchievement:
    return UnlockAchievement(
        achievement_id=id,
        title=title,
        reward=reward,
        layer=layer,
        description=description,
    )


def spawn_once(
    state, monster_id: str, role: str, pos: tuple[int, int], fallback: tuple[int, int] | None = None
) -> SpawnMonster | None:
    if monster_id in state.monsters:
        return None
    spawn_pos = pos
    if state.entity_at(spawn_pos) is not None:
        spawn_pos = fallback
    if spawn_pos is None or state.entity_at(spawn_pos) is not None:
        return None
    return SpawnMonster(monster_id=monster_id, role=role, pos=spawn_pos)


def alert(message: str, amount: int = 1) -> list[Effect]:
    return [ModifyAlert(amount=amount), EmitEvent(message=message)]


def tick(key: str) -> IncrementCounter:
    return IncrementCounter(key=key)
