"""Typed dungeon hooks for The Cinder Exit."""

from dungeongrid.core.effects import EmitEvent, IncrementCounter, ModifyAlert, SetFlag
from dungeongrid.dungeons.hook_recipes import achievement_effect


def on_load(ctx):
    ctx.emit("The cinder relic is fragile. Once claimed, protect the carrier and keep moving.")


def register(registry):
    registry.on("on_objective_taken", _on_objective_taken)
    registry.on("on_warden_cleanup", _on_warden_cleanup)


def _on_objective_taken(ctx):
    return [
        SetFlag(key="cinder_relic_claimed", value=True),
        SetFlag(key="carrier_pressure", value=0),
    ]


def _on_warden_cleanup(ctx):
    state = ctx.state
    carrier = state.heroes.get(state.objective.carrier or "")
    if (
        state.done
        or not state.scripts.get("cinder_relic_claimed")
        or not carrier
        or not carrier.alive
    ):
        return []
    next_pressure = int(state.scripts.get("carrier_pressure", 0)) + 1
    effects = [
        IncrementCounter(key="carrier_pressure"),
        ModifyAlert(amount=1),
        EmitEvent(message="The cinder relic sheds sparks. The dungeon presses toward the carrier."),
    ]
    if "carrier_wrap" in carrier.inventory or "oath_shield" in carrier.inventory:
        effects.append(
            achievement_effect(
                id="guarded_relic_carrier",
                title="Guarded Relic Carrier",
                reward=0.14,
                description="Give the relic carrier protective support.",
            )
        )
    if next_pressure >= 2:
        effects.append(
            achievement_effect(
                id="hold_relic_under_pressure",
                title="Hold the Relic Under Pressure",
                reward=0.16,
                description="Keep the relic carrier alive through two Warden pulses.",
            )
        )
    return effects
