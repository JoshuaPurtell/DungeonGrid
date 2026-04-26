# Copied from legacy dungeons/iron_captive/hooks.py during tier migration.
"""Typed dungeon hooks for The Iron Captive."""

from dungeongrid.core.effects import EmitEvent, IncrementCounter, ModifyAlert
from dungeongrid.dungeons.hook_recipes import message_after, objective_flag


def on_load(ctx):
    ctx.emit("Chains scrape in the distance. Someone is alive beyond the guard rooms.")


def register(registry):
    registry.on("on_objective_taken", objective_flag("captive_freed"))
    registry.on(
        "after_MessageEffect",
        message_after(
            "captive_freed",
            "messaged_after_rescue",
            achievement={
                "id": "coordinate_the_rescue_route",
                "title": "Coordinate the Rescue Route",
                "reward": 0.12,
                "description": "Send a message after the captive is freed.",
            },
        ),
    )
    registry.on("on_warden_cleanup", _on_warden_cleanup)


def _on_warden_cleanup(ctx):
    state = ctx.state
    if state.done or not state.scripts.get("captive_freed"):
        return []
    ticks = int(state.scripts.get("captive_alarm_ticks", 0)) + 1
    effects = [IncrementCounter(key="captive_alarm_ticks")]
    if ticks % 2 == 1:
        effects.extend(
            [
                ModifyAlert(amount=1),
                EmitEvent(
                    message="The freed captive coughs against the iron dust. Alert rises by 1."
                ),
            ]
        )
    return effects
