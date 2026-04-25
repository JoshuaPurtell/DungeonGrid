"""Typed dungeon hooks for Hourglass Escape."""

from dungeongrid.core.effects import EmitEvent, IncrementCounter, ModifyAlert, SetFlag
from dungeongrid.dungeons.hook_recipes import (
    achievement_effect,
    clue_flags,
    message_after,
    spawn_once,
)


def on_load(ctx):
    ctx.emit("Sand whispers behind the walls. The dungeon is already counting.")


def register(registry):
    registry.on("on_objective_taken", _on_objective_taken)
    registry.on(
        "on_furniture_searched",
        clue_flags(
            {"sand_table_1", "escape_marker_1"}, "escape_route_read", "escape_route_read_before_key"
        ),
    )
    registry.on(
        "after_MessageEffect",
        message_after(
            "hourglass_key_taken",
            "escape_count_called",
            achievement={
                "id": "call_the_count",
                "title": "Call the Count",
                "reward": 0.10,
                "description": "Send a message after the hourglass key is taken.",
            },
        ),
    )
    registry.on("after_Move", _after_move)
    registry.on("on_warden_cleanup", _on_warden_cleanup)


def _on_objective_taken(ctx):
    effects = [
        SetFlag(key="hourglass_key_taken", value=True),
        SetFlag(key="key_taken_round", value=ctx.state.round),
    ]
    if ctx.state.scripts.get("escape_route_read_before_key"):
        effects.append(
            achievement_effect(
                id="route_before_clock",
                title="Route Before Clock",
                reward=0.12,
                description="Read an escape route before carrying the hourglass key.",
            )
        )
    if ctx.state.round <= 8:
        effects.append(
            achievement_effect(
                id="beat_the_first_turn",
                title="Beat the First Turn",
                reward=0.14,
                description="Take the hourglass key by round 8.",
            )
        )
    return effects


def _after_move(ctx):
    if ctx.state.scripts.get("hourglass_key_taken"):
        return [SetFlag(key="moved_after_key", value=True)]
    return []


def _on_warden_cleanup(ctx):
    state = ctx.state
    if state.done:
        return []
    if not state.scripts.get("hourglass_key_taken"):
        if state.round >= int(state.scripts.get("round_limit_soft", 18)) // 2:
            return [
                ModifyAlert(amount=1),
                EmitEvent(message="The untouched hourglass rattles. Alert rises by 1."),
            ]
        return []
    ticks = int(state.scripts.get("escape_countdown_ticks", 0)) + 1
    effects = [IncrementCounter(key="escape_countdown_ticks")]
    if ticks == 1:
        spawn = spawn_once(state, "sand_wight_1", "lantern_wight", (10, 4), (9, 4))
        effects.append(EmitEvent(message="A sand-wight pours itself out of the archive wall."))
        if spawn:
            effects.append(spawn)
    else:
        effects.extend(
            [ModifyAlert(amount=1), EmitEvent(message="More sand falls. Alert rises by 1.")]
        )
    return effects
