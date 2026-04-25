"""Typed dungeon hooks for The Ashen Pantry."""

from dungeongrid.dungeons.hook_recipes import achievement_effect


def on_load(ctx):
    ctx.emit("Ash muffles sound in the pantry. Searching shelves and walls can save a long route.")


def register(registry):
    registry.on("after_RevealSecretDoor", _after_secret_revealed)


def _after_secret_revealed(ctx):
    effect = ctx.info.get("trigger_payload", {}).get("effect", {})
    if effect.get("door_id") == "secret_1":
        return [
            achievement_effect(
                id="spot_pantry_shortcut",
                title="Spot the Pantry Shortcut",
                reward=0.10,
                description="Reveal the hidden shortcut before opening it.",
            )
        ]
    return []
