"""Typed dungeon hooks for Magistrate Gold."""

from dungeongrid.core.effects import EmitEvent, ModifyAlert, SetFlag
from dungeongrid.dungeons.hook_recipes import achievement_effect, clue_flags, message_after, objective_flag, spawn_once


def on_load(ctx):
    ctx.emit("The magistrate vault smells of dust, wax, and hidden accounting.")


def register(registry):
    registry.on("on_objective_taken", objective_flag("strongbox_taken"))
    registry.on("on_furniture_searched", clue_flags({"ledger_table_1"}, "ledger_checked", "ledger_checked_before_strongbox"))
    registry.on("on_objective_taken", _ledger_achievement)
    registry.on("after_MessageEffect", message_after("strongbox_taken", "planned_strongbox_retreat", achievement={"id": "call_the_getaway", "title": "Call the Getaway", "reward": 0.10, "description": "Send a message after taking the strongbox."}))
    registry.on("on_warden_cleanup", _on_warden_cleanup)


def _ledger_achievement(ctx):
    if ctx.state.scripts.get("ledger_checked_before_strongbox"):
        return [achievement_effect(id="audit_before_theft", title="Audit Before Theft", reward=0.12, description="Check the ledger before carrying the strongbox.")]
    return []


def _on_warden_cleanup(ctx):
    state = ctx.state
    if state.done or not state.scripts.get("strongbox_taken"):
        return []
    if not state.scripts.get("seal_guard_spawned"):
        spawn = spawn_once(state, "seal_guard_1", "bone_guard", (10, 12), (9, 12))
        effects = [SetFlag(key="seal_guard_spawned", value=True), EmitEvent(message="The seal chime pulls a guard out from the lower vault.")]
        if spawn:
            effects.append(spawn)
        return effects
    return [ModifyAlert(amount=1), EmitEvent(message="The strongbox keeps chiming. Alert rises by 1.")]
