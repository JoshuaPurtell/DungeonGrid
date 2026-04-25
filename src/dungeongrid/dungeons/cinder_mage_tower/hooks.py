"""Typed dungeon hooks for Cinder Mage Tower."""

from dungeongrid.core.effects import (
    EmitEvent,
    IncrementCounter,
    ModifyAlert,
    SetFlag,
    SpawnMonster,
    UnlockAchievement,
)


def on_load(ctx):
    ctx.emit("The cinder tower breathes through its furnace stones.")


def register(registry):
    registry.on("on_objective_taken", _on_objective_taken)
    registry.on("after_AttackRoll", _after_attack_roll)
    registry.on("after_MessageEffect", _after_message)
    registry.on("on_warden_cleanup", _on_warden_cleanup)
    registry.on("on_furniture_searched", _on_furniture_searched)
    registry.on("on_furniture_destroyed", _on_furniture_destroyed)


def _on_objective_taken(ctx):
    if ctx.info.get("trigger_payload", {}).get("objective_id") != ctx.state.objective.id:
        return []
    effects = [SetFlag(key="cinder_focus_taken", value=True)]
    if ctx.state.scripts.get("tower_fixture_checked_before_focus"):
        effects.append(
            UnlockAchievement(
                achievement_id="understood_the_focus",
                title="Understood the Focus",
                reward=0.12,
                description="Check a tower fixture before carrying the focus.",
            )
        )
    return effects


def _after_attack_roll(ctx):
    effect = ctx.info.get("trigger_payload", {}).get("effect", {})
    if ctx.state.scripts.get("cinder_focus_taken") and effect.get("ranged"):
        return [
            SetFlag(key="covered_hot_retreat", value=True),
            UnlockAchievement(
                achievement_id="cover_the_hot_retreat",
                title="Cover the Hot Retreat",
                reward=0.12,
                description="Make a ranged attack after the focus is taken.",
            ),
        ]
    return []


def _after_message(ctx):
    if not ctx.state.scripts.get("cinder_focus_taken"):
        return []
    return [
        SetFlag(key="called_hot_retreat", value=True),
        UnlockAchievement(
            achievement_id="call_the_hot_retreat",
            title="Call the Hot Retreat",
            reward=0.10,
            description="Send a message after the focus is taken.",
        ),
    ]


def _on_warden_cleanup(ctx):
    state = ctx.state
    if state.done or not state.scripts.get("cinder_focus_taken"):
        return []
    next_pulse = int(state.scripts.get("focus_heat_pulses", 0)) + 1
    effects = [IncrementCounter(key="focus_heat_pulses")]
    if next_pulse == 1:
        effects.extend(
            [
                EmitEvent(message="A cinder-wight forms in the library smoke."),
                SpawnMonster(
                    monster_id="cinder_wight_1",
                    role="lantern_wight",
                    pos=(10, 4) if state.entity_at((10, 4)) is None else (9, 4),
                    status=_monster_status(state, "lantern_wight"),
                ),
            ]
        )
    elif state.scripts.get("focus_ring_broken") or state.scripts.get("furnace_valve_broken"):
        effects.append(
            EmitEvent(message="The damaged tower focus vents wide instead of tracking the carrier.")
        )
    else:
        effects.extend(
            [
                ModifyAlert(amount=1),
                EmitEvent(message="The tower vents heat through the open route. Alert rises by 1."),
            ]
        )
    return effects


def _on_furniture_searched(ctx):
    state = ctx.state
    result = ctx.info.get("trigger_payload", {})
    target = result.get("furniture_id")
    effects = []
    if target in {"spell_lectern_1", "focus_ring_1", "furnace_valve_1"}:
        effects.append(SetFlag(key="tower_fixture_checked", value=True))
        if state.objective.carrier is None:
            effects.append(SetFlag(key="tower_fixture_checked_before_focus", value=True))
    if target == "spell_lectern_1":
        effects.extend(
            [
                SetFlag(key="focus_formula_read", value=True),
                UnlockAchievement(
                    achievement_id="read_the_focus_formula",
                    title="Read the Focus Formula",
                    reward=0.12,
                    description="Search the lectern and learn the tower focus counterplay.",
                ),
            ]
        )
    if target == "furnace_valve_1":
        effects.append(SetFlag(key="furnace_valve_understood", value=True))
    return effects


def _on_furniture_destroyed(ctx):
    result = ctx.info.get("trigger_payload", {})
    if not result.get("destroyed"):
        return []
    target = result.get("furniture_id")
    if target == "focus_ring_1":
        return [
            SetFlag(key="focus_ring_broken", value=True),
            UnlockAchievement(
                achievement_id="crack_the_focus_ring",
                title="Crack the Focus Ring",
                reward=0.14,
                description="Destroy the focus ring and weaken the cinder pressure.",
            ),
        ]
    if target == "furnace_valve_1":
        return [
            SetFlag(key="furnace_valve_broken", value=True),
            UnlockAchievement(
                achievement_id="vent_the_furnace",
                title="Vent the Furnace",
                reward=0.14,
                description="Break the furnace valve to disrupt the tower heat.",
            ),
        ]
    return []


def _monster_status(state, role):
    status = []
    if role == "lantern_wight" and state.scripts.get("focus_formula_read"):
        status.append("vulnerable")
    if role == "lantern_wight" and (
        state.scripts.get("focus_ring_broken") or state.scripts.get("furnace_valve_broken")
    ):
        status.append("weakened")
    return status
