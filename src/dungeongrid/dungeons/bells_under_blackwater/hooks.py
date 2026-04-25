"""Typed dungeon hooks for Bells Under Blackwater."""

from dungeongrid.core.effects import EmitEvent, IncrementCounter, ModifyAlert, SetFlag
from dungeongrid.dungeons.hook_recipes import achievement_effect, spawn_once


def on_load(ctx):
    ctx.state.scripts.setdefault("bell_alarm_timer", 2)
    ctx.emit(
        "Water carries a distant bell note. The rite will escalate if the bell keeper is ignored."
    )


def register(registry):
    registry.on("after_Damage", _after_damage)
    registry.on("on_warden_cleanup", _on_warden_cleanup)


def _after_damage(ctx):
    effect = ctx.info.get("trigger_payload", {}).get("effect", {})
    target = ctx.state.monsters.get(str(effect.get("target_id")))
    if target and target.role == "gloom_cultist" and not target.alive:
        return [
            SetFlag(key="bell_keeper_silenced", value=True),
            EmitEvent(message="The bell note falters as the keeper falls."),
        ]
    return []


def _on_warden_cleanup(ctx):
    state = ctx.state
    if (
        state.done
        or state.scripts.get("bell_alarm_triggered")
        or state.scripts.get("bell_keeper_silenced")
    ):
        return []
    cultist = state.monsters.get("gloom_cultist_1")
    if not cultist or not cultist.alive:
        return [SetFlag(key="bell_keeper_silenced", value=True)]
    timer = int(state.scripts.get("bell_alarm_timer", 2)) - 1
    effects = [IncrementCounter(key="bell_alarm_timer", amount=-1, default=2)]
    if timer > 0:
        effects.append(
            EmitEvent(message=f"The bell keeper chants. Alarm will ring in {timer} Warden phase.")
        )
        return effects
    effects.extend(
        [
            SetFlag(key="bell_alarm_triggered", value=True),
            ModifyAlert(amount=3),
            achievement_effect(
                id="survive_bell_alarm",
                title="Survive the Bell Alarm",
                reward=0.16,
                description="Endure the first Warden alarm pulse.",
            ),
            EmitEvent(
                message="The bell rings under blackwater. Reinforcements surface from the channel."
            ),
        ]
    )
    for spawn in (
        spawn_once(state, "bone_guard_alarm", "bone_guard", (16, 8), None),
        spawn_once(state, "skitterling_alarm", "skitterling", (14, 12), None),
    ):
        if spawn:
            effects.append(spawn)
    return effects
