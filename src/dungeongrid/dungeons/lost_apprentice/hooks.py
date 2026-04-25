"""Typed dungeon hooks for The Lost Apprentice."""

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
    ctx.emit("A student's chalk marks lead inward, then double back over themselves.")


def register(registry):
    registry.on("on_objective_taken", objective_flag("apprentice_found"))
    registry.on(
        "on_furniture_searched",
        clue_flags(
            {"chalk_board_1", "lower_notes_1"},
            "sigil_clue_read",
            "sigil_clue_read_before_apprentice",
        ),
    )
    registry.on("on_objective_taken", _clue_achievement)
    registry.on(
        "after_MessageEffect",
        message_after(
            "apprentice_found",
            "apprentice_route_called",
            achievement={
                "id": "call_the_rescue_route",
                "title": "Call the Rescue Route",
                "reward": 0.10,
                "description": "Send a message after finding the apprentice.",
            },
        ),
    )
    registry.on(
        "after_Guard",
        guard_after(
            "apprentice_found",
            "apprentice_guarded",
            achievement={
                "id": "bodyguard_the_apprentice",
                "title": "Bodyguard the Apprentice",
                "reward": 0.12,
                "description": "Use guard after the apprentice is found.",
            },
        ),
    )
    registry.on("on_warden_cleanup", _on_warden_cleanup)


def _clue_achievement(ctx):
    if ctx.state.scripts.get("sigil_clue_read_before_apprentice"):
        return [
            achievement_effect(
                id="found_the_right_formula",
                title="Found the Right Formula",
                reward=0.12,
                description="Read a sigil clue before escorting the apprentice.",
            )
        ]
    return []


def _on_warden_cleanup(ctx):
    state = ctx.state
    if state.done or not state.scripts.get("apprentice_found"):
        return []
    pulses = int(state.scripts.get("apprentice_spell_pulses", 0)) + 1
    effects = [IncrementCounter(key="apprentice_spell_pulses")]
    if pulses == 1:
        spawn = spawn_once(state, "miscast_hunter_1", "lantern_wight", (10, 4), (9, 4))
        effects.append(
            EmitEvent(message="The miscast spell folds into a pale hunter near the archive.")
        )
        if spawn:
            effects.append(spawn)
    elif pulses % 2 == 0:
        effects.extend(
            [
                ModifyAlert(amount=1),
                EmitEvent(message="The apprentice's spell sputters loudly. Alert rises by 1."),
            ]
        )
    return effects
