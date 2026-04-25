"""Typed dungeon hooks for Return to Hollow Barrow."""

from dungeongrid.core.effects import EmitEvent, IncrementCounter, ModifyAlert
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
    ctx.emit("The barrow recognizes the party. The old silence is gone.")


def register(registry):
    registry.on("on_objective_taken", objective_flag("hollow_sigil_taken"))
    registry.on(
        "on_furniture_searched",
        clue_flags(
            {"king_tablet_1", "last_path_marker_1"},
            "king_route_read",
            "king_route_read_before_sigil",
        ),
    )
    registry.on("on_objective_taken", _route_achievement)
    registry.on(
        "after_MessageEffect",
        message_after(
            "hollow_sigil_taken",
            "final_retreat_called",
            achievement={
                "id": "call_the_final_retreat",
                "title": "Call the Final Retreat",
                "reward": 0.12,
                "description": "Send a message after the Hollow King's sigil is taken.",
            },
        ),
    )
    registry.on(
        "after_Guard",
        guard_after(
            "hollow_sigil_taken",
            "final_line_held",
            achievement={
                "id": "hold_the_final_line",
                "title": "Hold the Final Line",
                "reward": 0.14,
                "description": "Use guard after the Hollow King's sigil is taken.",
            },
        ),
    )
    registry.on(
        "after_AttackRoll",
        attack_after(
            "hollow_sigil_taken",
            "faced_the_king",
            ranged=False,
            achievement={
                "id": "face_the_hollow_king",
                "title": "Face the Hollow King",
                "reward": 0.14,
                "description": "Make a melee attack after the Hollow King's sigil is taken.",
            },
        ),
    )
    registry.on(
        "after_AttackRoll",
        attack_after(
            "hollow_sigil_taken",
            "covered_final_retreat",
            ranged=True,
            achievement={
                "id": "cover_the_final_retreat",
                "title": "Cover the Final Retreat",
                "reward": 0.14,
                "description": "Make a ranged attack after the Hollow King's sigil is taken.",
            },
        ),
    )
    registry.on("on_warden_cleanup", _on_warden_cleanup)


def _route_achievement(ctx):
    if ctx.state.scripts.get("king_route_read_before_sigil"):
        return [
            achievement_effect(
                id="remember_the_old_route",
                title="Remember the Old Route",
                reward=0.14,
                description="Read the final route before carrying the sigil.",
            )
        ]
    return []


def _on_warden_cleanup(ctx):
    state = ctx.state
    if state.done or not state.scripts.get("hollow_sigil_taken"):
        return []
    ticks = int(state.scripts.get("hollow_return_ticks", 0)) + 1
    effects = [IncrementCounter(key="hollow_return_ticks")]
    schedule = {
        1: (
            "hollow_king_return_1",
            "lantern_wight",
            (10, 4),
            (9, 4),
            "The Hollow King's shadow fills the archive wall.",
        ),
        2: (
            "last_path_guard_1",
            "bone_guard",
            (5, 12),
            (9, 4),
            "A funeral guard closes the last path.",
        ),
        3: (
            "sigil_skitterling_1",
            "skitterling",
            (7, 8),
            (9, 4),
            "A skitterling follows the sigil's dust through the crossing.",
        ),
    }
    if ticks in schedule:
        monster_id, role, pos, fallback, message = schedule[ticks]
        spawn = spawn_once(state, monster_id, role, pos, fallback)
        effects.append(EmitEvent(message=message))
        if spawn:
            effects.append(spawn)
    else:
        effects.extend(
            [
                ModifyAlert(amount=1),
                EmitEvent(message="The Hollow King names the carrier again. Alert rises by 1."),
            ]
        )
    return effects
