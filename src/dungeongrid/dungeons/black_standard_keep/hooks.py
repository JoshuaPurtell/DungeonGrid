"""Typed dungeon hooks for Black Standard Keep."""

from dungeongrid.core.effects import EmitEvent, IncrementCounter, ModifyAlert
from dungeongrid.dungeons.hook_recipes import achievement_effect, attack_after, clue_flags, guard_after, message_after, objective_flag, spawn_once


def on_load(ctx):
    ctx.emit("The keep is awake even before the first gate opens.")


def register(registry):
    registry.on("on_objective_taken", objective_flag("black_standard_taken"))
    registry.on("on_furniture_searched", clue_flags({"signal_table_1"}, "watch_rotation_read", "watch_rotation_read_before_standard"))
    registry.on("on_objective_taken", _intel_achievement)
    registry.on("after_MessageEffect", message_after("black_standard_taken", "standard_retreat_called", achievement={"id": "call_the_standard_retreat", "title": "Call the Standard Retreat", "reward": 0.10, "description": "Send a message after the black standard is taken."}))
    registry.on("after_Guard", guard_after("black_standard_taken", "standard_line_held", achievement={"id": "hold_the_keep_line", "title": "Hold the Keep Line", "reward": 0.12, "description": "Use guard after the black standard is taken."}))
    registry.on("after_AttackRoll", attack_after("black_standard_taken", "standard_retreat_covered", ranged=True, achievement={"id": "cover_the_keep_retreat", "title": "Cover the Keep Retreat", "reward": 0.12, "description": "Make a ranged attack after the black standard is taken."}))
    registry.on("on_warden_cleanup", _on_warden_cleanup)


def _intel_achievement(ctx):
    if ctx.state.scripts.get("watch_rotation_read_before_standard"):
        return [achievement_effect(id="breach_with_intel", title="Breach With Intel", reward=0.12, description="Read the keep watch rotation before carrying the standard.")]
    return []


def _on_warden_cleanup(ctx):
    state = ctx.state
    if state.done:
        return []
    effects = []
    if any(m.alive and m.role == "gloom_cultist" for m in state.monsters.values()) and state.round % 3 == 0:
        effects.extend([ModifyAlert(amount=1), EmitEvent(message="A keep caller beats the signal rhythm. Alert rises by 1.")])
    if not state.scripts.get("black_standard_taken"):
        return effects
    ticks = int(state.scripts.get("standard_alarm_ticks", 0)) + 1
    effects.append(IncrementCounter(key="standard_alarm_ticks"))
    if ticks == 1:
        spawn = spawn_once(state, "reserve_guard_1", "bone_guard", (5, 12), (6, 12))
        effects.append(EmitEvent(message="A reserve guard enters the lower barracks route."))
        if spawn:
            effects.append(spawn)
    elif ticks == 2:
        spawn = spawn_once(state, "standard_skitterling_1", "skitterling", (7, 8), (6, 12))
        effects.append(EmitEvent(message="A skitterling cuts across the shield hall."))
        if spawn:
            effects.append(spawn)
    else:
        effects.extend([ModifyAlert(amount=1), EmitEvent(message="The black standard drags attention like a torch. Alert rises by 1.")])
    return effects
