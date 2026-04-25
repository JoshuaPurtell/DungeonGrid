"""Typed dungeon hooks for The Glass Maze."""

from dungeongrid.core.effects import EmitEvent, IncrementCounter, ModifyAlert
from dungeongrid.dungeons.hook_recipes import (
    achievement_effect,
    clue_flags,
    message_after,
    objective_flag,
    spawn_once,
)


def on_load(ctx):
    ctx.emit("The glass maze reflects the party from angles that do not quite exist.")


def register(registry):
    registry.on("on_objective_taken", objective_flag("mirror_prism_taken"))
    registry.on(
        "on_furniture_searched", clue_flags({"mirror_stand_1", "lower_map_1"}, "maze_clue_read")
    )
    registry.on("after_MessageEffect", _after_message)
    registry.on("on_warden_cleanup", _on_warden_cleanup)


def _after_message(ctx):
    effects = []
    if ctx.state.scripts.get("mirror_prism_taken"):
        effects.extend(
            message_after(
                "mirror_prism_taken",
                "shared_prism_route",
                achievement={
                    "id": "call_the_prism_route",
                    "title": "Call the Prism Route",
                    "reward": 0.10,
                    "description": "Send a route message after taking the prism.",
                },
            )(ctx)
        )
    if ctx.state.scripts.get("maze_clue_read"):
        effects.append(
            achievement_effect(
                id="share_the_maze_clue",
                title="Share the Maze Clue",
                reward=0.12,
                description="Read a maze clue and send a party message.",
            )
        )
    return effects


def _on_warden_cleanup(ctx):
    state = ctx.state
    if state.done or not state.scripts.get("mirror_prism_taken"):
        return []
    pulses = int(state.scripts.get("prism_pulses", 0)) + 1
    effects = [IncrementCounter(key="prism_pulses")]
    if pulses == 1:
        spawn = spawn_once(state, "reflected_hunter_1", "lantern_wight", (10, 4), (9, 4))
        effects.append(EmitEvent(message="A reflected hunter steps out of the wrong corridor."))
        if spawn:
            effects.append(spawn)
    elif pulses % 2 == 0:
        effects.extend(
            [
                ModifyAlert(amount=1),
                EmitEvent(message="The prism flashes through the walls. Alert rises by 1."),
            ]
        )
    return effects
