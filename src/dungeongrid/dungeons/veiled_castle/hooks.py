"""Typed dungeon hooks for Veiled Castle."""

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
    ctx.emit("The veiled castle offers too many clean routes, which is the first warning.")


def register(registry):
    registry.on("on_objective_taken", objective_flag("veiled_signet_taken"))
    registry.on(
        "on_furniture_searched",
        clue_flags({"portrait_wall_1", "servants_map_1"}, "true_route_read"),
    )
    registry.on("after_MessageEffect", _after_message)
    registry.on(
        "after_Guard",
        guard_after(
            "veiled_signet_taken",
            "guarded_signet_route",
            achievement={
                "id": "hold_the_signet_route",
                "title": "Hold the Signet Route",
                "reward": 0.12,
                "description": "Use guard after the signet is taken.",
            },
        ),
    )
    registry.on("on_warden_cleanup", _on_warden_cleanup)


def _after_message(ctx):
    effects = []
    if ctx.state.scripts.get("true_route_read"):
        effects.append(
            achievement_effect(
                id="share_the_true_route",
                title="Share the True Route",
                reward=0.12,
                description="Read a route clue and send a party message.",
            )
        )
    if ctx.state.scripts.get("veiled_signet_taken"):
        effects.extend(
            message_after(
                "veiled_signet_taken",
                "shared_signet_escape",
                achievement={
                    "id": "call_the_signet_escape",
                    "title": "Call the Signet Escape",
                    "reward": 0.10,
                    "description": "Send a message after the signet is taken.",
                },
            )(ctx)
        )
    return effects


def _on_warden_cleanup(ctx):
    state = ctx.state
    if state.done or not state.scripts.get("veiled_signet_taken"):
        return []
    ticks = int(state.scripts.get("veil_ticks", 0)) + 1
    effects = [IncrementCounter(key="veil_ticks")]
    if ticks == 1:
        spawn = spawn_once(state, "veiled_watcher_1", "lantern_wight", (10, 4), (9, 4))
        effects.append(EmitEvent(message="A veiled watcher steps through the portrait wall."))
        if spawn:
            effects.append(spawn)
    elif ticks % 2 == 0:
        effects.extend(
            [
                ModifyAlert(amount=1),
                EmitEvent(message="The castle stops pretending to be empty. Alert rises by 1."),
            ]
        )
    return effects
