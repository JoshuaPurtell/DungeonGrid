"""Typed dungeon hooks for The Lantern Crypt."""

from dungeongrid.core.effects import (
    EmitEvent,
    IncrementCounter,
    ModifyAlert,
    SetFlag,
    SpawnMonster,
    UnlockAchievement,
)


def on_load(ctx):
    ctx.emit("The crypt air smells of cold ash. The ember idol is quiet for now.")


def register(registry):
    registry.on("on_objective_taken", _on_objective_taken)
    registry.on("on_furniture_searched", _on_furniture_searched)
    registry.on("on_furniture_destroyed", _on_furniture_destroyed)
    registry.on("on_warden_cleanup", _on_warden_cleanup)


def _on_objective_taken(ctx):
    if ctx.info.get("trigger_payload", {}).get("objective_id") != ctx.state.objective.id:
        return []
    return [
        SetFlag(key="ember_idol_taken", value=True),
        SetFlag(key="idol_pulse_count", value=0),
    ]


def _on_furniture_searched(ctx):
    result = ctx.info.get("trigger_payload", {})
    target = result.get("furniture_id")
    if target == "ember_altar_1":
        return [
            SetFlag(key="ember_altar_read", value=True),
            UnlockAchievement(
                achievement_id="read_ember_tether",
                title="Read the Ember Tether",
                reward=0.12,
                description="Search the ember altar and reveal the wight's weakness.",
            ),
        ]
    if target == "weapon_rack_1":
        return [SetFlag(key="crypt_weapon_rack_searched", value=True)]
    return []


def _on_furniture_destroyed(ctx):
    result = ctx.info.get("trigger_payload", {})
    if result.get("furniture_id") != "ember_altar_1" or not result.get("destroyed"):
        return []
    return [
        SetFlag(key="ember_altar_destroyed", value=True),
        UnlockAchievement(
            achievement_id="break_the_ember_altar",
            title="Break the Ember Altar",
            reward=0.14,
            description="Destroy the altar that feeds the idol's pursuit.",
        ),
    ]


def _on_warden_cleanup(ctx):
    state = ctx.state
    if state.done or not state.scripts.get("ember_idol_taken"):
        return []
    next_pulse = int(state.scripts.get("idol_pulse_count", 0)) + 1
    effects = [IncrementCounter(key="idol_pulse_count")]
    if next_pulse == 1:
        status = _wight_status(state)
        effects.extend(
            [
                EmitEvent(
                    message="The ember idol pulses. A lantern-wight pulls itself out of the lower wall."
                ),
                SpawnMonster(
                    monster_id="lantern_wight_1",
                    role="lantern_wight",
                    pos=_spawn_pos(state),
                    status=status,
                ),
                UnlockAchievement(
                    achievement_id="survive_first_idol_pulse",
                    title="Survive the First Idol Pulse",
                    reward=0.14,
                    description="Carry the idol through its first Warden pulse.",
                ),
            ]
        )
    elif next_pulse % 2 == 0:
        effects.extend(
            [
                ModifyAlert(amount=1),
                EmitEvent(message="The idol's light beats like a warning bell. Alert rises by 1."),
            ]
        )
    return effects


def _wight_status(state):
    status = []
    if state.scripts.get("ember_altar_read"):
        status.append("vulnerable")
    if state.scripts.get("ember_altar_destroyed"):
        status.append("weakened")
    return status


def _spawn_pos(state):
    configured = state.scripts.get("lantern_wight_spawn")
    candidates = []
    if isinstance(configured, list) and len(configured) == 2:
        candidates.append((int(configured[0]), int(configured[1])))
    candidates.extend([(8, 12), (9, 12), state.objective.pos, state.entry])
    for pos in candidates:
        x, y = pos
        if (
            0 <= x < state.width
            and 0 <= y < state.height
            and state.terrain[y][x] == "."
            and state.entity_at(pos) is None
        ):
            return pos
    return state.entry
