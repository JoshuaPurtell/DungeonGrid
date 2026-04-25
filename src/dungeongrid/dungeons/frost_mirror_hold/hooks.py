"""Typed dungeon hooks for Frost Mirror Hold."""

from dungeongrid.core.effects import EmitEvent, IncrementCounter, ModifyAlert
from dungeongrid.dungeons.hook_recipes import achievement_effect, attack_after, clue_flags, guard_after, message_after, objective_flag, spawn_once


def on_load(ctx):
    ctx.emit("The frost mirror hold is silent except for distant cracking ice.")


def register(registry):
    registry.on("on_objective_taken", objective_flag("frost_mirror_taken"))
    registry.on("on_furniture_searched", clue_flags({"reflection_slate_1", "thaw_marker_1"}, "thaw_route_read", "thaw_route_read_before_mirror"))
    registry.on("on_objective_taken", _route_achievement)
    registry.on("after_MessageEffect", message_after("frost_mirror_taken", "frost_route_called", achievement={"id": "call_the_cold_route", "title": "Call the Cold Route", "reward": 0.10, "description": "Send a message after the frost mirror is taken."}))
    registry.on("after_Guard", guard_after("frost_mirror_taken", "frost_carrier_guarded", achievement={"id": "guard_the_frost_carrier", "title": "Guard the Frost Carrier", "reward": 0.12, "description": "Use guard after the frost mirror is taken."}))
    registry.on("after_AttackRoll", attack_after("frost_mirror_taken", "frost_retreat_covered", ranged=True, achievement={"id": "cover_the_frost_retreat", "title": "Cover the Frost Retreat", "reward": 0.12, "description": "Make a ranged attack after the frost mirror is taken."}))
    registry.on("on_warden_cleanup", _on_warden_cleanup)


def _route_achievement(ctx):
    if ctx.state.scripts.get("thaw_route_read_before_mirror"):
        return [achievement_effect(id="plan_the_thaw_route", title="Plan the Thaw Route", reward=0.12, description="Read the thaw route before carrying the frost mirror.")]
    return []


def _on_warden_cleanup(ctx):
    state = ctx.state
    if state.done or not state.scripts.get("frost_mirror_taken"):
        return []
    ticks = int(state.scripts.get("frost_ticks", 0)) + 1
    effects = [IncrementCounter(key="frost_ticks")]
    if ticks == 1:
        spawn = spawn_once(state, "frost_wight_1", "lantern_wight", (10, 4), (9, 4))
        effects.append(EmitEvent(message="A frost-wight steps out of the mirror script."))
        if spawn:
            effects.append(spawn)
    elif ticks == 2:
        spawn = spawn_once(state, "frozen_guard_1", "bone_guard", (5, 12), (9, 4))
        effects.append(EmitEvent(message="A frozen guard blocks part of the lower thaw route."))
        if spawn:
            effects.append(spawn)
    else:
        effects.extend([ModifyAlert(amount=1), EmitEvent(message="The carrier's breath marks the way. Alert rises by 1.")])
    return effects
