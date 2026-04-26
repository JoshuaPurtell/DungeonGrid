# Copied from legacy dungeons/low_shrine_locks/hooks.py during tier migration.
"""Typed dungeon hooks for Three Locks of the Low Shrine."""

from dungeongrid.core.effects import EmitEvent, SetFlag
from dungeongrid.dungeons.hook_recipes import achievement_effect


def on_load(ctx):
    ctx.emit("Three shrine caches answer the central lock. Splitting search routes can save torch.")


def register(registry):
    registry.on("after_AddInventory", _check_tokens)
    registry.on("after_TransferItem", _check_tokens)


def _check_tokens(ctx):
    state = ctx.state
    if state.scripts.get("shrine_core_unlocked"):
        return []
    tokens = sum(hero.inventory.count("shrine_token") for hero in state.heroes.values())
    if tokens < int(state.scripts.get("token_requirement", 2)):
        return []
    return [
        SetFlag(key="shrine_core_unlocked", value=True),
        achievement_effect(
            id="unlock_shrine_core",
            title="Unlock the Shrine Core",
            reward=0.22,
            description="Bring enough tokens together to open the central lock.",
        ),
        EmitEvent(message="The low shrine core unlocks as the matching tokens answer each other."),
    ]
