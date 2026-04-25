"""Typed dungeon hooks for Barrow of the Hollow King."""

from dungeongrid.core.effects import EmitEvent, IncrementCounter, ModifyAlert, SetFlag
from dungeongrid.dungeons.hook_recipes import (
    achievement_effect,
    attack_after,
    clue_flags,
    guard_after,
    message_after,
    objective_flag,
    spawn_once,
)


def on_load(ctx):
    ctx.emit("The barrow breathes once, slowly, as the party enters.")


def register(registry):
    registry.on("on_objective_taken", objective_flag("hollow_crown_taken"))
    registry.on("on_furniture_searched", clue_flags({"ancestor_masks_1", "crypt_marker_1"}, "funeral_path_read", "funeral_path_read_before_crown"))
    registry.on("after_MessageEffect", message_after("hollow_crown_taken", "crown_retreat_called", achievement={"id": "call_the_crown_retreat", "title": "Call the Crown Retreat", "reward": 0.10, "description": "Send a message after the hollow crown is taken."}))
    registry.on("after_Guard", guard_after("hollow_crown_taken", "crown_line_held", achievement={"id": "hold_back_the_barrow", "title": "Hold Back the Barrow", "reward": 0.12, "description": "Use guard after the hollow crown is taken."}))
    registry.on("after_AttackRoll", attack_after("hollow_crown_taken", "stood_against_undead", ranged=False, achievement={"id": "stand_against_the_dead", "title": "Stand Against the Dead", "reward": 0.12, "description": "Make a melee attack after the hollow crown is taken."}))
    registry.on("on_objective_taken", _route_achievement)
    registry.on("on_warden_cleanup", _on_warden_cleanup)


def _route_achievement(ctx):
    if ctx.state.scripts.get("funeral_path_read_before_crown"):
        return [achievement_effect(id="know_the_funeral_path", title="Know the Funeral Path", reward=0.12, description="Read the funeral path before carrying the crown.")]
    return []


def _on_warden_cleanup(ctx):
    state = ctx.state
    if state.done or not state.scripts.get("hollow_crown_taken"):
        return []
    ticks = int(state.scripts.get("hollow_king_ticks", 0)) + 1
    effects = [IncrementCounter(key="hollow_king_ticks")]
    if ticks == 1:
        spawn = spawn_once(state, "hollow_king_shadow_1", "lantern_wight", (10, 4), (9, 4))
        effects.append(EmitEvent(message="The Hollow King's shadow separates from the throne wall."))
        if spawn:
            effects.append(spawn)
    elif ticks == 2:
        spawn = spawn_once(state, "funeral_guard_1", "bone_guard", (5, 12), (9, 4))
        effects.append(EmitEvent(message="A funeral guard rises from the lower loop."))
        if spawn:
            effects.append(spawn)
    else:
        effects.extend([ModifyAlert(amount=1), EmitEvent(message="The crown whispers the carrier's route aloud. Alert rises by 1.")])
    return effects
