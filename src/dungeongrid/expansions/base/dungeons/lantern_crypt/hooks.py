# Copied from legacy dungeons/lantern_crypt/hooks.py during tier migration.
"""Typed dungeon hooks for The Lantern Crypt."""

from dungeongrid.core.effects import (
    EmitEvent,
    IncrementCounter,
    ModifyAlert,
    SetFlag,
    SpawnMonster,
    UnlockAchievement,
)


def on_load(ctx):
    ctx.emit("The crypt air smells of cold ash. The ember idol is quiet for now.")


def register(registry):
    registry.on("on_objective_taken", _on_objective_taken)
    registry.on("on_furniture_searched", _on_furniture_searched)
    registry.on("on_furniture_destroyed", _on_furniture_destroyed)
    registry.on("on_warden_cleanup", _on_warden_cleanup)
    registry.on("after_Guard", _after_heavy_guard)
    registry.on("after_AttackRoll", _after_heavy_attack_roll)
    registry.on("after_MessageEffect", _after_heavy_message)
    registry.on("after_SearchArea", _after_heavy_search_area)
    registry.on("on_furniture_searched", _on_heavy_furniture_searched)
    registry.on("on_objective_taken", _on_heavy_objective_taken)


def _on_objective_taken(ctx):
    if ctx.info.get("trigger_payload", {}).get("objective_id") != ctx.state.objective.id:
        return []
    return [
        SetFlag(key="ember_idol_taken", value=True),
        SetFlag(key="idol_pulse_count", value=0),
    ]


def _on_furniture_searched(ctx):
    result = ctx.info.get("trigger_payload", {})
    target = result.get("furniture_id")
    if target == "ember_altar_1":
        return [
            SetFlag(key="ember_altar_read", value=True),
            UnlockAchievement(
                achievement_id="read_ember_tether",
                title="Read the Ember Tether",
                reward=0.12,
                description="Search the ember altar and reveal the wight's weakness.",
            ),
        ]
    if target == "weapon_rack_1":
        return [SetFlag(key="crypt_weapon_rack_searched", value=True)]
    return []


def _on_furniture_destroyed(ctx):
    result = ctx.info.get("trigger_payload", {})
    if result.get("furniture_id") != "ember_altar_1" or not result.get("destroyed"):
        return []
    return [
        SetFlag(key="ember_altar_destroyed", value=True),
        UnlockAchievement(
            achievement_id="break_the_ember_altar",
            title="Break the Ember Altar",
            reward=0.14,
            description="Destroy the altar that feeds the idol's pursuit.",
        ),
    ]


def _on_warden_cleanup(ctx):
    state = ctx.state
    if state.done or not state.scripts.get("ember_idol_taken"):
        return []
    next_pulse = int(state.scripts.get("idol_pulse_count", 0)) + 1
    effects = [IncrementCounter(key="idol_pulse_count")]
    if next_pulse == 1:
        status = _wight_status(state)
        effects.extend(
            [
                EmitEvent(
                    message="The ember idol pulses. A lantern-wight pulls itself out of the lower wall."
                ),
                SpawnMonster(
                    monster_id="lantern_wight_1",
                    role="lantern_wight",
                    pos=(8, 12) if state.entity_at((8, 12)) is None else (9, 12),
                    status=status,
                ),
                UnlockAchievement(
                    achievement_id="survive_first_idol_pulse",
                    title="Survive the First Idol Pulse",
                    reward=0.14,
                    description="Carry the idol through its first Warden pulse.",
                ),
            ]
        )
    elif next_pulse % 2 == 0:
        effects.extend(
            [
                ModifyAlert(amount=1),
                EmitEvent(message="The idol's light beats like a warning bell. Alert rises by 1."),
            ]
        )
    return effects


def _wight_status(state):
    status = []
    if state.scripts.get("ember_altar_read"):
        status.append("vulnerable")
    if state.scripts.get("ember_altar_destroyed"):
        status.append("weakened")
    return status



def _is_heavy_lantern(ctx):
    return ctx.state.quest_id == "base:lantern_crypt:heavy" or ctx.state.scripts.get("tier") == "heavy"


def _role(ctx, hero_id):
    hero = ctx.state.heroes.get(hero_id)
    return hero.role if hero else ""


def _after_heavy_guard(ctx):
    if not _is_heavy_lantern(ctx):
        return []
    actor_id = ctx.info.get("trigger_payload", {}).get("effect", {}).get("actor_id")
    if _role(ctx, actor_id) != "barbarian":
        return []
    effects = [SetFlag(key="heavy_barbarian_screened", value=True)]
    if ctx.state.scripts.get("heavy_wizard_counterplay"):
        effects.append(
            UnlockAchievement(
                achievement_id="heavy_barbarian_screens_reader",
                title="Screen The Reader",
                reward=0.12,
                description="Use the Barbarian to guard after the Wizard has engaged the altar counterplay.",
            )
        )
    return effects


def _after_heavy_attack_roll(ctx):
    if not _is_heavy_lantern(ctx):
        return []
    effect = ctx.info.get("trigger_payload", {}).get("effect", {})
    if _role(ctx, effect.get("attacker_id")) != "barbarian":
        return []
    if not (ctx.state.scripts.get("ember_altar_read") or ctx.state.scripts.get("ember_altar_destroyed")):
        return []
    return [
        SetFlag(key="heavy_barbarian_committed_after_counterplay", value=True),
        UnlockAchievement(
            achievement_id="heavy_commit_after_counterplay",
            title="Commit After Counterplay",
            reward=0.12,
            description="Use Barbarian pressure after the altar has been read or broken.",
        ),
    ]


def _after_heavy_message(ctx):
    if not _is_heavy_lantern(ctx):
        return []
    if not (ctx.state.scripts.get("ember_altar_read") or ctx.state.scripts.get("ember_altar_destroyed")):
        return []
    return [
        SetFlag(key="heavy_counterplay_called", value=True),
        UnlockAchievement(
            achievement_id="heavy_call_the_counterplay",
            title="Call The Counterplay",
            reward=0.10,
            description="Send a party message after the altar clue or break changes the fight.",
        ),
    ]


def _after_heavy_search_area(ctx):
    if not _is_heavy_lantern(ctx):
        return []
    effect = ctx.info.get("trigger_payload", {}).get("effect", {})
    if _role(ctx, effect.get("actor_id")) != "dwarf":
        return []
    if effect.get("category") not in {"secrets", "glyphs"}:
        return []
    return [
        SetFlag(key="heavy_dwarf_checked_secret_route", value=True),
        UnlockAchievement(
            achievement_id="heavy_dwarf_checks_secret_route",
            title="Dwarf Checks The Secret Route",
            reward=0.10,
            description="Use the Dwarf to check route hazards or secrets before the idol run.",
        ),
    ]


def _on_heavy_furniture_searched(ctx):
    if not _is_heavy_lantern(ctx):
        return []
    result = ctx.info.get("trigger_payload", {})
    target = result.get("furniture_id")
    role = result.get("role")
    effects = []
    if target == "ember_altar_1" and role == "wizard":
        effects.extend(
            [
                SetFlag(key="heavy_wizard_counterplay", value=True),
                UnlockAchievement(
                    achievement_id="heavy_wizard_reads_altar",
                    title="Wizard Reads The Altar",
                    reward=0.12,
                    description="Use the Wizard for the counterplay clue instead of treating the fight as raw damage.",
                ),
            ]
        )
    if target == "lantern_lens_1" and role == "elf":
        effects.extend(
            [
                SetFlag(key="heavy_elf_scouted_lens", value=True),
                UnlockAchievement(
                    achievement_id="heavy_elf_confirms_tether",
                    title="Elf Confirms The Tether",
                    reward=0.10,
                    description="Use the Elf to scout the lens route and confirm how the altar connects to the idol room.",
                ),
            ]
        )
    if target == "route_mark_1" and role == "dwarf":
        effects.extend(
            [
                SetFlag(key="heavy_dwarf_marked_route", value=True),
                UnlockAchievement(
                    achievement_id="heavy_dwarf_marks_route",
                    title="Dwarf Marks The Route",
                    reward=0.10,
                    description="Use the Dwarf to mark the secret return route before the idol is carried.",
                ),
            ]
        )
    if ctx.state.scripts.get("heavy_elf_scouted_lens") and ctx.state.scripts.get("heavy_dwarf_marked_route"):
        effects.append(
            UnlockAchievement(
                achievement_id="heavy_elf_dwarf_route_pair",
                title="Elf-Dwarf Route Pair",
                reward=0.14,
                description="Pair Elf scouting with Dwarf route marking before the final idol run.",
            )
        )
    if ctx.state.scripts.get("heavy_wizard_counterplay") and ctx.state.scripts.get("heavy_barbarian_screened"):
        effects.append(
            UnlockAchievement(
                achievement_id="heavy_wizard_barbarian_tandem",
                title="Wizard-Barbarian Tandem",
                reward=0.14,
                description="Pair Wizard counterplay with Barbarian screening at the ember crossing.",
            )
        )
    return effects


def _on_heavy_objective_taken(ctx):
    if not _is_heavy_lantern(ctx):
        return []
    if ctx.info.get("trigger_payload", {}).get("objective_id") != ctx.state.objective.id:
        return []
    required = (
        "heavy_wizard_counterplay",
        "heavy_barbarian_screened",
        "heavy_elf_scouted_lens",
        "heavy_dwarf_marked_route",
    )
    if all(ctx.state.scripts.get(key) for key in required):
        return [
            UnlockAchievement(
                achievement_id="heavy_four_role_counterplay",
                title="Four-Role Counterplay",
                reward=0.22,
                description="Use Wizard, Barbarian, Elf, and Dwarf contributions before taking the idol.",
            )
        ]
    return []
