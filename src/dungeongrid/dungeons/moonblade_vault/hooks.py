"""Typed dungeon hooks for Moonblade Vault."""

from dungeongrid.core.effects import EmitEvent, IncrementCounter, ModifyAlert, SetFlag
from dungeongrid.dungeons.hook_recipes import achievement_effect, attack_after, clue_flags, guard_after, message_after, spawn_once


def on_load(ctx):
    ctx.emit("The moonblade vault is bright enough to cast shadows upward.")


def register(registry):
    registry.on("on_objective_taken", _on_objective_taken)
    registry.on("on_furniture_searched", clue_flags({"moon_phase_table_1", "silver_route_marker_1"}, "bearer_oath_read", "bearer_oath_read_before_blade"))
    registry.on("after_MessageEffect", message_after("moonblade_taken", "moonblade_route_called", achievement={"id": "call_the_blade_route", "title": "Call the Blade Route", "reward": 0.10, "description": "Send a message after the moonblade is taken."}))
    registry.on("after_Guard", guard_after("moonblade_taken", "moonblade_bearer_guarded", achievement={"id": "guard_the_blade_bearer", "title": "Guard the Blade Bearer", "reward": 0.12, "description": "Use guard after the moonblade is taken."}))
    registry.on("after_AttackRoll", attack_after("moonblade_taken", "moonblade_retreat_covered", ranged=True, achievement={"id": "cover_the_blade_retreat", "title": "Cover the Blade Retreat", "reward": 0.12, "description": "Make a ranged attack after the moonblade is taken."}))
    registry.on("on_warden_cleanup", _on_warden_cleanup)


def _on_objective_taken(ctx):
    effects = [SetFlag(key="moonblade_taken", value=True), SetFlag(key="moonblade_bearer", value=ctx.state.objective.carrier)]
    if ctx.state.scripts.get("bearer_oath_read_before_blade"):
        effects.append(achievement_effect(id="choose_the_blade_bearer", title="Choose the Blade Bearer", reward=0.12, description="Read the bearer oath before carrying the moonblade."))
    return effects


def _on_warden_cleanup(ctx):
    state = ctx.state
    if state.done or not state.scripts.get("moonblade_taken"):
        return []
    ticks = int(state.scripts.get("moonblade_ticks", 0)) + 1
    effects = [IncrementCounter(key="moonblade_ticks")]
    if ticks == 1:
        spawn = spawn_once(state, "moonlit_watcher_1", "lantern_wight", (10, 4), (9, 4))
        effects.append(EmitEvent(message="A moonlit watcher slips out from the archive wall."))
        if spawn:
            effects.append(spawn)
    elif ticks == 2:
        spawn = spawn_once(state, "silver_guard_1", "bone_guard", (5, 12), (9, 4))
        effects.append(EmitEvent(message="A silver guard steps onto the lower escort route."))
        if spawn:
            effects.append(spawn)
    else:
        effects.extend([ModifyAlert(amount=1), EmitEvent(message="The moonblade keeps singing the bearer's location. Alert rises by 1.")])
    return effects
