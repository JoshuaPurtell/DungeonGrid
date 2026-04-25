"""Typed dungeon hooks for Trial of Embers."""

from dungeongrid.core.effects import EmitEvent, IncrementCounter, ModifyAlert, SetFlag
from dungeongrid.dungeons.hook_recipes import achievement_effect, objective_flag, spawn_once


def on_load(ctx):
    ctx.emit("The trial hall is warm enough to breathe ash. The old floor still judges movement.")


def register(registry):
    registry.on("on_objective_taken", objective_flag("ember_oath_taken"))
    registry.on("after_DisarmTrap", _after_disarm)
    registry.on("on_warden_cleanup", _on_warden_cleanup)


def _after_disarm(ctx):
    if ctx.state.scripts.get("ember_oath_taken"):
        return [
            SetFlag(key="late_disarm_after_oath", value=True),
            achievement_effect(
                id="keep_calm_after_the_oath",
                title="Keep Calm After the Oath",
                reward=0.12,
                description="Disarm a hazard after the objective wakes the trial.",
            ),
        ]
    return []


def _on_warden_cleanup(ctx):
    state = ctx.state
    if state.done or not state.scripts.get("ember_oath_taken"):
        return []
    pulses = int(state.scripts.get("oath_pulses", 0)) + 1
    effects = [IncrementCounter(key="oath_pulses")]
    if pulses == 1:
        spawn = spawn_once(state, "trial_watcher_1", "skitterling", (13, 10), (14, 10))
        effects.append(
            EmitEvent(message="The lower embers knit themselves into a skittering watcher.")
        )
        if spawn:
            effects.append(spawn)
    elif pulses % 2 == 0:
        effects.extend(
            [
                ModifyAlert(amount=1),
                EmitEvent(message="The oath answers with a hot pulse. Alert rises by 1."),
            ]
        )
    return effects
