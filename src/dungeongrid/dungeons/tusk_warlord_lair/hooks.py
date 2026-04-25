"""Typed dungeon hooks for Tusk Warlord Lair."""

from dungeongrid.core.effects import (
    EmitEvent,
    ModifyAlert,
    SetFlag,
    SpawnMonster,
    UnlockAchievement,
)


def on_load(ctx):
    ctx.emit("A low drumbeat moves through the lair. The standard is somewhere past the bone gate.")


def register(registry):
    registry.on("on_objective_taken", _on_objective_taken)
    registry.on("after_AttackRoll", _after_attack_roll)
    registry.on("on_warden_cleanup", _on_warden_cleanup)
    registry.on("on_furniture_searched", _on_furniture_searched)
    registry.on("on_furniture_destroyed", _on_furniture_destroyed)


def _on_objective_taken(ctx):
    if ctx.info.get("trigger_payload", {}).get("objective_id") != ctx.state.objective.id:
        return []
    return [SetFlag(key="standard_taken", value=True)]


def _after_attack_roll(ctx):
    effect = ctx.info.get("trigger_payload", {}).get("effect", {})
    if ctx.state.scripts.get("standard_taken") and effect.get("ranged"):
        return [
            SetFlag(key="covered_retreat", value=True),
            UnlockAchievement(
                achievement_id="cover_the_standard_retreat",
                title="Cover the Standard Retreat",
                reward=0.12,
                description="Make a ranged attack after the standard is taken.",
            ),
        ]
    return []


def _on_warden_cleanup(ctx):
    state = ctx.state
    if state.done:
        return []
    effects = []
    if state.alert >= 3 and not state.scripts.get("drum_reinforcement_spawned") and not state.scripts.get("war_drum_broken"):
        effects.extend(
            [
                SetFlag(key="drum_reinforcement_spawned", value=True),
                EmitEvent(message="The war drum booms. A fresh skitterling darts from the lower pen."),
                SpawnMonster(monster_id="drum_skitterling_1", role="skitterling", pos=(8, 12) if state.entity_at((8, 12)) is None else (9, 12)),
            ]
        )
    if state.scripts.get("standard_taken"):
        effects.extend(
            [
                ModifyAlert(amount=1),
                EmitEvent(message="The torn standard leaves a visible trail. Alert rises by 1."),
            ]
        )
    return effects


def _on_furniture_searched(ctx):
    result = ctx.info.get("trigger_payload", {})
    target = result.get("furniture_id")
    if target == "war_drum_1":
        return [
            SetFlag(key="war_drum_understood", value=True),
            UnlockAchievement(
                achievement_id="understand_the_war_drum",
                title="Understand the War Drum",
                reward=0.10,
                description="Search the war drum and identify the alarm loop.",
            ),
        ]
    if target == "trophy_rack_1":
        return [
            SetFlag(key="warlord_trophy_rack_read", value=True),
            UnlockAchievement(
                achievement_id="read_the_warlord_trophies",
                title="Read the Warlord Trophies",
                reward=0.12,
                description="Search the trophy rack and expose the commander's weakness.",
            ),
        ]
    return []


def _on_furniture_destroyed(ctx):
    result = ctx.info.get("trigger_payload", {})
    if result.get("furniture_id") != "war_drum_1" or not result.get("destroyed"):
        return []
    return [
        SetFlag(key="war_drum_broken", value=True),
        UnlockAchievement(
            achievement_id="silence_the_war_drum",
            title="Silence the War Drum",
            reward=0.16,
            description="Destroy the war drum before it can coordinate the lair.",
        ),
    ]
