"""Typed dungeon hooks for Broken Oath Ambush."""

from dungeongrid.core.effects import EmitEvent, IncrementCounter, ModifyAlert
from dungeongrid.dungeons.hook_recipes import (
    achievement_effect,
    clue_flags,
    guard_after,
    message_after,
    objective_flag,
    spawn_once,
)


def on_load(ctx):
    ctx.emit("The oath hall is too quiet. Every door sounds like it has witnesses.")


def register(registry):
    registry.on("on_objective_taken", objective_flag("broken_seal_taken"))
    registry.on(
        "on_furniture_searched",
        clue_flags({"oath_table_1"}, "ambush_clause_read", "ambush_clause_read_before_seal"),
    )
    registry.on("on_objective_taken", _clue_achievement)
    registry.on(
        "after_MessageEffect",
        message_after(
            "broken_seal_taken",
            "retreat_called",
            achievement={
                "id": "call_the_broken_retreat",
                "title": "Call the Broken Retreat",
                "reward": 0.10,
                "description": "Send a message after the ambush begins.",
            },
        ),
    )
    registry.on(
        "after_Guard",
        guard_after(
            "broken_seal_taken",
            "guarded_retreat",
            achievement={
                "id": "hold_the_retreat_line",
                "title": "Hold the Retreat Line",
                "reward": 0.12,
                "description": "Use guard after the broken seal is taken.",
            },
        ),
    )
    registry.on("on_warden_cleanup", _on_warden_cleanup)


def _clue_achievement(ctx):
    if ctx.state.scripts.get("ambush_clause_read_before_seal"):
        return [
            achievement_effect(
                id="knew_it_was_a_trap",
                title="Knew It Was a Trap",
                reward=0.12,
                description="Read the ambush clause before carrying the seal.",
            )
        ]
    return []


def _on_warden_cleanup(ctx):
    state = ctx.state
    if state.done or not state.scripts.get("broken_seal_taken"):
        return []
    ticks = int(state.scripts.get("ambush_ticks", 0)) + 1
    effects = [IncrementCounter(key="ambush_ticks")]
    if ticks == 1:
        spawn = spawn_once(state, "witness_guard_1", "bone_guard", (5, 12), (6, 12))
        effects.append(EmitEvent(message="A witness guard steps into the lower route."))
        if spawn:
            effects.append(spawn)
    elif ticks == 2:
        spawn = spawn_once(state, "echo_skitterling_1", "skitterling", (7, 8), (6, 12))
        effects.append(
            EmitEvent(message="A skitterling follows the carrier's echo through the center floor.")
        )
        if spawn:
            effects.append(spawn)
    else:
        effects.extend(
            [
                ModifyAlert(amount=1),
                EmitEvent(message="The oath hall keeps naming the carrier. Alert rises by 1."),
            ]
        )
    return effects
