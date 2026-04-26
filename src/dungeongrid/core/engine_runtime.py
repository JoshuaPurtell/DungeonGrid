"""State-machine runtime and typed effect resolver for DungeonGrid."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Iterable
from dataclasses import asdict, is_dataclass
from enum import Enum
from typing import Any

from .data import (
    ACTION_COSTS,
    ARMOR_ITEMS,
    DIRECTIONS,
    HERO_ARCHETYPES,
    MAJOR_ACTION_TYPES,
    MONSTER_TYPES,
    SPELL_CARDS,
    WEAPON_ITEMS,
    Entity,
    GameState,
    Pos,
    default_per_hero_stats,
)
from .effects import (
    ActivateMonster,
    AddInventory,
    AdvancePhase,
    ApplyStatus,
    AttackRoll,
    BossDefeated,
    BossPhaseChange,
    CallExtraction,
    CastSpell,
    Damage,
    DamageFurniture,
    DisarmTrap,
    DrawCard,
    Effect,
    EmitEvent,
    EndTurn,
    EquipItem,
    ExtractHero,
    Guard,
    Heal,
    IncrementCounter,
    MarkMajorAction,
    MessageEffect,
    ModifyAlert,
    ModifyDread,
    MonsterAct,
    Move,
    ObjectiveEscape,
    ObjectiveTake,
    OpenChest,
    OpenDoor,
    PayAP,
    Phase,
    RemoveInventory,
    RemoveStatus,
    RevealSecretDoor,
    RevealTrap,
    SearchArea,
    SearchFurniture,
    SetFlag,
    SpawnMonster,
    SpawnMonsterNear,
    SpendMovement,
    Timing,
    TransferItem,
    UnlockAchievement,
    UseItem,
    ValidationFailure,
    WardenSpendDread,
)
from .message_protocol import protocol_from_state


class TriggerRegistry:
    """Small deterministic trigger registry for engine and dungeon hooks."""

    def __init__(self) -> None:
        self._handlers: dict[str, list[Callable[[ResolverContext], Iterable[Effect] | None]]] = (
            defaultdict(list)
        )

    def on(
        self, event_name: str, handler: Callable[[ResolverContext], Iterable[Effect] | None]
    ) -> None:
        self._handlers[event_name].append(handler)

    def handlers(
        self, event_name: str
    ) -> list[Callable[[ResolverContext], Iterable[Effect] | None]]:
        return list(self._handlers.get(event_name, []))

    def emit(self, event_name: str, ctx: ResolverContext) -> list[Effect]:
        effects: list[Effect] = []
        for handler in self._handlers.get(event_name, []):
            produced = handler(ctx)
            if produced:
                effects.extend(produced)
        return effects


class ResolverContext:
    """Mutable context passed through effect resolution and triggers."""

    def __init__(
        self,
        *,
        state: GameState,
        runtime: EngineRuntime,
        actor_id: str,
        action: dict[str, Any],
    ) -> None:
        self.state = state
        self.runtime = runtime
        self.actor_id = actor_id
        self.action = action
        self.reward = 0.0
        self.texts: list[str] = []
        self.info: dict[str, Any] = {}
        self.resolved_effects: list[dict[str, Any]] = []
        self.triggered_reactions: list[dict[str, Any]] = []

    def emit_text(self, text: str) -> None:
        if text:
            self.texts.append(text)

    def add_reward(self, reward: float) -> None:
        self.reward += max(0.0, reward)


class EffectResolver:
    """The central mutation boundary for GameState."""

    def __init__(self, runtime: EngineRuntime) -> None:
        self.runtime = runtime

    def resolve_many(self, ctx: ResolverContext, effects: Iterable[Effect]) -> None:
        queue = list(effects)
        while queue:
            effect = queue.pop(0)
            ctx.resolved_effects.append(self._effect_record(effect))
            followups = self.resolve(ctx, effect)
            if followups:
                queue[0:0] = list(followups)
            reactions = self.runtime.emit_trigger(
                ctx, f"after_{effect.kind}", {"effect": self._effect_record(effect)}
            )
            if reactions:
                ctx.triggered_reactions.extend(self._effect_record(item) for item in reactions)
                queue[0:0] = reactions

    def resolve(self, ctx: ResolverContext, effect: Effect) -> list[Effect]:
        if isinstance(effect, PayAP):
            state = ctx.state
            state.ap_remaining[effect.entity_id] = max(
                0, state.ap_remaining.get(effect.entity_id, 0) - effect.amount
            )
            return []
        if isinstance(effect, SpendMovement):
            state = ctx.state
            state.movement_remaining[effect.entity_id] = max(
                0,
                state.movement_remaining.get(effect.entity_id, 0) - max(0, effect.amount),
            )
            return []
        if isinstance(effect, MarkMajorAction):
            ctx.state.major_action_used[effect.entity_id] = True
            ctx.state.trace.append(
                {
                    "kind": "major_action_used",
                    "round": ctx.state.round,
                    "agent_id": effect.entity_id,
                    "action_type": effect.action_type,
                }
            )
            return []
        if isinstance(effect, Move):
            entity = ctx.state.all_entities().get(effect.entity_id)
            if not entity:
                return []
            entity.pos = effect.to
            ctx.emit_text(f"{entity.role} moves {effect.direction}.")
            trap = ctx.state.trap_at(effect.to)
            if trap and trap.armed and entity.team == "heroes":
                return [
                    RevealTrap(trap_id=trap.id, disarm=True),
                    Damage(
                        source_id=trap.id, target_id=entity.id, amount=trap.damage, source="trap"
                    ),
                ]
            return []
        if isinstance(effect, OpenDoor):
            state = ctx.state
            hero = state.heroes.get(effect.actor_id)
            door = state.doors[effect.door_id]
            door.state = "open"
            if door.secret:
                door.discovered = True
            self.runtime.grid.update_known_tiles(state)
            self.runtime.grid.update_revealed_rooms(
                state, reason="door_opened", opener_id=effect.actor_id
            )
            if effect.actor_id in state.heroes:
                state.scripts["last_room_revealer"] = effect.actor_id
                state.scripts["last_room_revealer_round"] = state.round
            state.alert += 1
            if effect.actor_id in state.heroes:
                stats = state.per_hero_stats.setdefault(
                    effect.actor_id, default_per_hero_stats(state.heroes[effect.actor_id])
                )
                stats["doors_opened"] = int(stats.get("doors_opened", 0)) + 1
            ctx.add_reward(0.02)
            ctx.emit_text(
                f"{hero.role if hero else effect.actor_id} opens {door.id}; the passage beyond is now visible."
            )
            return []
        if isinstance(effect, AttackRoll):
            return self._resolve_attack_roll(ctx, effect)
        if isinstance(effect, CastSpell):
            return self._resolve_cast_spell(ctx, effect)
        if isinstance(effect, Damage):
            return self._resolve_damage(ctx, effect)
        if isinstance(effect, BossPhaseChange):
            return self._resolve_boss_phase_change(ctx, effect)
        if isinstance(effect, BossDefeated):
            return self._resolve_boss_defeated(ctx, effect)
        if isinstance(effect, Heal):
            target = ctx.state.heroes.get(effect.target_id) or ctx.state.monsters.get(
                effect.target_id
            )
            if not target:
                return []
            healed = min(effect.amount, target.max_hp - target.hp)
            target.hp += healed
            ctx.add_reward(0.06 * healed if target.team == "heroes" else 0.0)
            ctx.emit_text(f"{target.role} restores {healed} hp.")
            return []
        if isinstance(effect, DrawCard):
            return self._resolve_draw_card(ctx, effect)
        if isinstance(effect, AddInventory):
            target = ctx.state.heroes.get(effect.target_id)
            if target and effect.item_id:
                target.inventory.append(effect.item_id)
                ctx.emit_text(f"{target.role} gains {self.runtime.item_name(effect.item_id)}.")
            return []
        if isinstance(effect, RemoveInventory):
            target = ctx.state.heroes.get(effect.target_id)
            if target and effect.item_id in target.inventory:
                target.inventory.remove(effect.item_id)
            return []
        if isinstance(effect, ApplyStatus):
            target = ctx.state.all_entities().get(effect.target_id)
            if target and effect.status and effect.status not in target.status:
                target.status.append(effect.status)
                ctx.emit_text(f"{target.role} gains {effect.status}.")
            return []
        if isinstance(effect, RemoveStatus):
            target = ctx.state.all_entities().get(effect.target_id)
            if target and effect.status in target.status:
                target.status.remove(effect.status)
            return []
        if isinstance(effect, RevealTrap):
            trap = ctx.state.traps.get(effect.trap_id)
            if trap:
                trap.revealed = True
                if effect.disarm:
                    trap.armed = False
                ctx.emit_text(f"{trap.id} is revealed.")
            return []
        if isinstance(effect, RevealSecretDoor):
            door = ctx.state.doors.get(effect.door_id)
            if door:
                door.discovered = True
                ctx.add_reward(0.08)
                ctx.emit_text(f"Secret door {door.id} is revealed.")
            return []
        if isinstance(effect, SpawnMonster):
            return self._resolve_spawn_monster(ctx, effect)
        if isinstance(effect, SpawnMonsterNear):
            return self._resolve_spawn_monster_near(ctx, effect)
        if isinstance(effect, ActivateMonster):
            monster = ctx.state.monsters.get(effect.monster_id)
            if monster and monster.alive:
                monster.activation = "engaged"
                ctx.emit_text(f"{monster.role} stirs.")
            return []
        if isinstance(effect, ModifyAlert):
            return [SetFlag(key="_alert_delta", value=effect.amount)]
        if isinstance(effect, ModifyDread):
            old_dread = ctx.state.dread
            cap = int(ctx.state.ruleset.get("warden_dread", {}).get("max", 6))
            ctx.state.dread = max(0, min(cap, ctx.state.dread + effect.amount))
            if ctx.state.dread != old_dread:
                ctx.state.trace.append(
                    {
                        "kind": "dread_changed",
                        "round": ctx.state.round,
                        "from": old_dread,
                        "to": ctx.state.dread,
                        "reason": effect.reason,
                    }
                )
                ctx.emit_text(f"Warden dread changes from {old_dread} to {ctx.state.dread}.")
            return []
        if isinstance(effect, WardenSpendDread):
            return self._resolve_warden_spend_dread(ctx, effect)
        if isinstance(effect, IncrementCounter):
            if effect.key.startswith("_social:"):
                metric = effect.key.split(":", 1)[1]
                self.runtime.increment_social_metric(ctx.state, metric, amount=effect.amount)
                return []
            current = int(ctx.state.scripts.get(effect.key, effect.default))
            ctx.state.scripts[effect.key] = current + effect.amount
            return []
        if isinstance(effect, SetFlag):
            if effect.key in {"_alert_delta", "_treasure_delta"}:
                ctx.state.scripts[effect.key] = int(ctx.state.scripts.get(effect.key, 0)) + int(
                    effect.value
                )
            else:
                ctx.state.scripts[effect.key] = effect.value
            return []
        if isinstance(effect, EmitEvent):
            if effect.message:
                ctx.state.event_log.append(effect.message)
                ctx.emit_text(effect.message)
            if effect.trace_kind:
                ctx.state.trace.append(
                    {"kind": effect.trace_kind, "round": ctx.state.round, **effect.payload_data}
                )
            return []
        if isinstance(effect, UnlockAchievement):
            achievement_id = effect.achievement_id
            if "." not in achievement_id:
                achievement_id = f"{ctx.state.quest_id}.{achievement_id}"
            if achievement_id not in ctx.state.achievements_unlocked:
                event = {
                    "id": achievement_id,
                    "title": effect.title
                    or achievement_id.rsplit(".", 1)[-1].replace("_", " ").title(),
                    "layer": effect.layer,
                    "reward": max(0.0, effect.reward),
                    "round": ctx.state.round,
                }
                if effect.description:
                    event["description"] = effect.description
                ctx.state.achievements_unlocked.add(achievement_id)
                ctx.state.achievement_events.append(event)
                ctx.state.achievement_reward += max(0.0, effect.reward)
                ctx.add_reward(effect.reward)
                ctx.state.event_log.append(f"Achievement unlocked: {event['title']}.")
            return []
        if isinstance(effect, TransferItem):
            source = ctx.state.heroes.get(effect.source_id)
            target = ctx.state.heroes.get(effect.target_id)
            if source and target and effect.item_id in source.inventory:
                source.inventory.remove(effect.item_id)
                target.inventory.append(effect.item_id)
                ctx.state.trace.append(
                    {
                        "kind": "item_given",
                        "round": ctx.state.round,
                        "agent_id": source.id,
                        "role": source.role,
                        "target_agent_id": target.id,
                        "target_role": target.role,
                        "item": effect.item_id,
                    }
                )
                self.runtime.increment_social_metric(ctx.state, "items_given")
                source_stats = ctx.state.per_hero_stats.setdefault(
                    source.id, default_per_hero_stats(source)
                )
                target_stats = ctx.state.per_hero_stats.setdefault(
                    target.id, default_per_hero_stats(target)
                )
                source_stats["items_given"] = int(source_stats.get("items_given", 0)) + 1
                target_stats["items_received"] = (
                    int(target_stats.get("items_received", 0)) + 1
                )
                if effect.item_id == ctx.state.objective.id:
                    self.runtime.increment_social_metric(ctx.state, "objective_passes")
                if effect.item_id == "healing_draught":
                    self.runtime.increment_social_metric(ctx.state, "healing_items_given")
                ctx.emit_text(f"{source.role} gives {effect.item_id} to {target.role}.")
                ctx.add_reward(0.02)
            return []
        if isinstance(effect, EquipItem):
            return self._resolve_equip_item(ctx, effect)
        if isinstance(effect, MessageEffect):
            result = protocol_from_state(ctx.state).submit(
                ctx.state,
                effect.actor_id,
                {
                    "type": "message",
                    "target": effect.target,
                    "payload": {"text": effect.text, **dict(effect.metadata)},
                },
            )
            if result.delivered and result.envelope:
                hero = ctx.state.heroes.get(effect.actor_id)
                if hero:
                    stats = ctx.state.per_hero_stats.setdefault(
                        hero.id, default_per_hero_stats(hero)
                    )
                    stats["messages_sent"] = int(stats.get("messages_sent", 0)) + 1
            ctx.info["message_result"] = {
                "accepted": result.accepted,
                "delivered": result.delivered,
                "queued": result.queued,
                "dropped": result.dropped,
                "reason": result.reason,
                "message": result.message,
            }
            ctx.emit_text(result.message)
            return []
        if isinstance(effect, Guard):
            hero = ctx.state.heroes.get(effect.actor_id)
            if hero and "guarded" not in hero.status:
                hero.status.append("guarded")
                ctx.add_reward(0.01)
                ctx.emit_text(f"{hero.role} takes a guarded stance.")
            return []
        if isinstance(effect, DisarmTrap):
            return self._resolve_disarm(ctx, effect)
        if isinstance(effect, OpenChest):
            return self._resolve_open_chest(ctx, effect)
        if isinstance(effect, SearchFurniture):
            return self._resolve_search_furniture(ctx, effect)
        if isinstance(effect, DamageFurniture):
            return self._resolve_damage_furniture(ctx, effect)
        if isinstance(effect, ObjectiveTake):
            hero = ctx.state.heroes[effect.actor_id]
            ctx.state.objective.carrier = hero.id
            ctx.state.objective.pos = None
            if ctx.state.objective.id not in hero.inventory:
                hero.inventory.append(ctx.state.objective.id)
            ctx.add_reward(0.25)
            ctx.emit_text(f"{hero.role} takes {ctx.state.objective.id}.")
            return [
                *self._script_effects(ctx, "on_objective_taken"),
                *self.runtime.emit_trigger(
                    ctx,
                    "on_objective_taken",
                    {"actor_id": hero.id, "objective_id": ctx.state.objective.id},
                ),
            ]
        if isinstance(effect, ObjectiveEscape):
            hero = ctx.state.heroes[effect.actor_id]
            return [ExtractHero(actor_id=hero.id, with_objective=True)]
        if isinstance(effect, ExtractHero):
            return self._resolve_extract_hero(ctx, effect)
        if isinstance(effect, CallExtraction):
            return self._resolve_call_extraction(ctx, effect)
        if isinstance(effect, SearchArea):
            return self._resolve_search_area(ctx, effect)
        if isinstance(effect, UseItem):
            return self._resolve_use_item(ctx, effect)
        if isinstance(effect, MonsterAct):
            return self._resolve_monster_act(ctx, effect)
        if isinstance(effect, EndTurn):
            hero = ctx.state.heroes.get(effect.actor_id)
            if hero:
                ctx.state.ap_remaining[hero.id] = 0
                ctx.emit_text(f"{hero.role} ends their turn.")
            return []
        if isinstance(effect, AdvancePhase):
            self.runtime.phase.advance(ctx.state, effect.target, ctx)
            return []
        return []

    def raw_effects(self, actor_id: str, furniture_id: str, raw_effect: Any) -> list[Effect]:
        effects: list[Effect] = []
        raw_list = raw_effect if isinstance(raw_effect, list) else [raw_effect]
        for raw in raw_list:
            payload = {"type": "draw_deck"} if raw == "draw_deck" else raw
            if isinstance(payload, str):
                payload = {"type": payload}
            if not isinstance(payload, dict):
                continue
            kind = str(payload.get("type", "emit"))
            item = str(payload.get("item", ""))
            if kind == "draw_deck":
                effects.append(
                    DrawCard(
                        actor_id=actor_id,
                        deck_id=str(payload.get("deck", "treasure")),
                        source_id=furniture_id,
                    )
                )
            elif kind in {"item", "weapon", "armor", "artifact"} and item:
                effects.append(AddInventory(target_id=actor_id, item_id=item))
            elif kind == "spell" and item:
                effects.append(
                    EmitEvent(
                        message=f"{item} spell card discovered.",
                        trace_kind="spell_card_found",
                        payload_data={"agent_id": actor_id, "spell": item},
                    )
                )
                effects.append(SetFlag(key=f"_grant_spell:{actor_id}:{item}", value=True))
            elif kind in {"gold", "treasure"}:
                amount = int(payload.get("amount", payload.get("treasure", 1)))
                for _ in range(max(1, amount)):
                    effects.append(AddInventory(target_id=actor_id, item_id="coin_cache"))
                effects.append(
                    SetFlag(key="_treasure_delta", value=int(payload.get("amount", amount)))
                )
            elif kind == "alert":
                effects.append(
                    SetFlag(
                        key="_alert_delta",
                        value=int(payload.get("amount", payload.get("alert", 1))),
                    )
                )
            elif kind == "dread":
                effects.append(
                    ModifyDread(
                        amount=int(payload.get("amount", payload.get("dread", 1))),
                        reason=str(payload.get("reason", "effect")),
                    )
                )
            elif kind in {"lower_alert", "suppress_alert"}:
                effects.append(
                    SetFlag(
                        key="_alert_delta",
                        value=-int(payload.get("amount", payload.get("alert", 1))),
                    )
                )
            elif kind == "increment_counter":
                effects.append(
                    IncrementCounter(
                        key=str(payload.get("key", "")),
                        amount=int(payload.get("amount", 1)),
                        default=int(payload.get("default", 0)),
                    )
                )
            elif kind == "damage":
                effects.append(
                    Damage(
                        source_id=furniture_id,
                        target_id=actor_id,
                        amount=int(payload.get("amount", payload.get("damage", 1))),
                        source="effect",
                    )
                )
            elif kind == "heal":
                effects.append(
                    Heal(
                        target_id=actor_id,
                        amount=int(payload.get("amount", payload.get("heal", 1))),
                    )
                )
            elif kind == "hero_status":
                effects.append(
                    ApplyStatus(target_id=actor_id, status=str(payload.get("status", "")))
                )
            elif kind in {"set_script", "set_flag"}:
                effects.append(
                    SetFlag(key=str(payload.get("key", "")), value=payload.get("value", True))
                )
            elif kind == "reveal":
                effects.append(SearchArea(actor_id=actor_id, category="glyphs"))
            elif kind == "monster_status":
                for monster in self.runtime.effect_target_monsters(
                    self.runtime.state_for_effects, payload
                ):
                    effects.append(
                        ApplyStatus(target_id=monster.id, status=str(payload.get("status", "")))
                    )
            elif kind == "spawn_monster":
                pos = payload.get("pos")
                effects.append(
                    SpawnMonster(
                        monster_id=str(payload.get("id", "")),
                        role=str(payload.get("role", "skitterling")),
                        pos=tuple(pos) if isinstance(pos, list) and len(pos) == 2 else None,
                        status=[str(item) for item in payload.get("status", [])]
                        if isinstance(payload.get("status"), list)
                        else [],
                    )
                )
            elif kind == "spawn_monster_near":
                fallback = payload.get("fallback_pos") or payload.get("pos")
                effects.append(
                    SpawnMonsterNear(
                        monster_id=str(payload.get("id", "")),
                        role=str(payload.get("role", "skitterling")),
                        anchor_id=str(payload.get("anchor_id", actor_id)),
                        fallback_pos=tuple(fallback)
                        if isinstance(fallback, list) and len(fallback) == 2
                        else None,
                        status=[str(item) for item in payload.get("status", [])]
                        if isinstance(payload.get("status"), list)
                        else [],
                    )
                )
            elif kind == "activate_monster":
                for monster in self.runtime.effect_target_monsters(
                    self.runtime.state_for_effects, payload
                ):
                    effects.append(ActivateMonster(monster_id=monster.id, reason="effect"))
            elif kind == "emit":
                effects.append(EmitEvent(message=str(payload.get("message", ""))))
            if payload.get("trace_kind"):
                effects.append(
                    EmitEvent(
                        message="",
                        trace_kind=str(payload["trace_kind"]),
                        payload_data={
                            "agent_id": actor_id,
                            "furniture_id": furniture_id,
                            "effect_type": kind,
                        },
                    )
                )
        return effects

    def _resolve_warden_spend_dread(
        self, ctx: ResolverContext, effect: WardenSpendDread
    ) -> list[Effect]:
        if ctx.state.dread < effect.cost:
            ctx.state.trace.append(
                {
                    "kind": "warden_dread_failed",
                    "round": ctx.state.round,
                    "effect": effect.effect,
                    "target_id": effect.target_id,
                    "dread": ctx.state.dread,
                }
            )
            return []
        ctx.state.dread -= effect.cost
        ctx.state.trace.append(
            {
                "kind": "warden_dread_spent",
                "round": ctx.state.round,
                "effect": effect.effect,
                "target_id": effect.target_id,
                "cost": effect.cost,
                "remaining_dread": ctx.state.dread,
            }
        )
        ctx.emit_text(f"The Warden spends dread on {effect.effect}.")
        if effect.effect == "spawn_wanderer":
            return [
                SpawnMonsterNear(
                    role="skitterling", anchor_id=effect.target_id, activation="engaged"
                )
            ]
        if effect.effect == "darken_lantern":
            old_torch = ctx.state.torch
            ctx.state.torch = max(0, ctx.state.torch - 2)
            ctx.emit_text(f"Torch drops from {old_torch} to {ctx.state.torch}.")
            return []
        if effect.effect == "pressure_carrier" and effect.target_id:
            return [
                ApplyStatus(target_id=effect.target_id, status="marked_by_warden", source="dread")
            ]
        if effect.effect == "block_extraction" and effect.target_id:
            return [
                SpawnMonsterNear(
                    role="bone_guard", anchor_id=effect.target_id, activation="engaged"
                )
            ]
        return []

    def _resolve_extract_hero(self, ctx: ResolverContext, effect: ExtractHero) -> list[Effect]:
        hero = ctx.state.heroes.get(effect.actor_id)
        if not hero or hero.id in ctx.state.extracted_heroes:
            return []
        carried_objective = ctx.state.objective.carrier == hero.id or effect.with_objective
        ctx.state.extracted_heroes.add(hero.id)
        stats = ctx.state.per_hero_stats.setdefault(hero.id, default_per_hero_stats(hero))
        stats["extracted"] = True
        ctx.state.extraction_events.append(
            {
                "round": ctx.state.round,
                "hero_id": hero.id,
                "role": hero.role,
                "carried_objective": carried_objective,
                "partial": effect.partial,
            }
        )
        ctx.state.trace.append(
            {
                "kind": "hero_extracted",
                "round": ctx.state.round,
                "agent_id": hero.id,
                "role": hero.role,
                "carried_objective": carried_objective,
                "partial": effect.partial,
            }
        )
        if carried_objective:
            ctx.state.objective.recovered = True
            ctx.state.objective.carrier = None
            if ctx.state.objective.id in hero.inventory:
                hero.inventory.remove(ctx.state.objective.id)
            ctx.add_reward(1.0)
        else:
            ctx.add_reward(0.12)
        if "extracted" not in hero.status:
            hero.status.append("extracted")
        ctx.state.ap_remaining[hero.id] = 0
        ctx.state.movement_remaining[hero.id] = 0
        ctx.emit_text(f"{hero.role} extracts{' with the objective' if carried_objective else ''}.")
        self.runtime.phase.check_end_conditions(ctx.state)
        return []

    def _resolve_call_extraction(
        self, ctx: ResolverContext, effect: CallExtraction
    ) -> list[Effect]:
        ctx.state.trace.append(
            {"kind": "extraction_called", "round": ctx.state.round, "agent_id": effect.actor_id}
        )
        ctx.state.done = True
        ctx.state.winner = "heroes"
        ctx.state.phase = "done"
        ctx.state.termination_reason = "partial_extraction"
        ctx.add_reward(0.35)
        ctx.emit_text("The party accepts a partial extraction.")
        return []

    def _resolve_attack_roll(self, ctx: ResolverContext, effect: AttackRoll) -> list[Effect]:
        attacker = ctx.state.all_entities().get(effect.attacker_id)
        target = ctx.state.all_entities().get(effect.target_id)
        if not attacker or not target:
            return []
        attack_dice = self.runtime.attack_dice(attacker, ranged=effect.ranged)
        if "weakened" in attacker.status:
            attack_dice = max(1, attack_dice - 1)
        hits = self.runtime.roll_successes(attack_dice)
        guard_dice = (
            self.runtime.hero_guard(target, ranged=effect.ranged)
            if target.team == "heroes"
            else target.guard
        )
        if "guarded" in target.status:
            guard_dice += 1
            target.status.remove("guarded")
        blocks = self.runtime.roll_successes(guard_dice)
        damage = max(0, hits - blocks)
        weapon = self.runtime.equipped_weapon(attacker)
        if damage and weapon:
            damage += int(weapon.get("bonus_damage_on_hit", 0))
        metadata = {
            "hits": hits,
            "blocks": blocks,
            "attack_dice": attack_dice,
            "ranged": effect.ranged,
        }
        ctx.emit_text(f"{attacker.role} attacks {target.role}: {hits} hits, {blocks} blocks.")
        return [
            Damage(
                source_id=attacker.id,
                target_id=target.id,
                amount=damage,
                source="attack",
                ranged=effect.ranged,
                metadata=metadata,
            )
        ]

    def _resolve_damage(self, ctx: ResolverContext, effect: Damage) -> list[Effect]:
        state = ctx.state
        target = state.all_entities().get(effect.target_id)
        source = state.all_entities().get(effect.source_id)
        if not target or not target.alive:
            return []
        amount = max(0, effect.amount)
        followups: list[Effect] = []
        if target.team == "dungeon" and source and source.team == "heroes":
            if "shielded" in target.status:
                amount = max(0, amount - 1)
            if "vulnerable" in target.status and amount > 0:
                amount += 1
            amount = self._monster_damage_prevention(ctx, source, target, amount)
        if target.team == "heroes":
            amount = self._hero_damage_prevention(ctx, target, amount, source_id=effect.source_id)
        target.hp -= amount
        if target.team == "heroes":
            state.total_damage_taken += amount
            target_stats = state.per_hero_stats.setdefault(
                target.id, default_per_hero_stats(target)
            )
            target_stats["damage_taken"] = int(target_stats.get("damage_taken", 0)) + amount
            ctx.add_reward(-0.1 * amount)
        else:
            if source and source.team == "heroes":
                source_stats = state.per_hero_stats.setdefault(
                    source.id, default_per_hero_stats(source)
                )
                source_stats["damage_dealt"] = (
                    int(source_stats.get("damage_dealt", 0)) + amount
                )
            ctx.add_reward(0.05 * amount)
        ctx.emit_text(f"{target.role} takes {amount} damage.")
        state.trace.append(
            {
                "kind": "damage",
                "round": state.round,
                "source_id": effect.source_id,
                "target_id": target.id,
                "target_role": target.role,
                "amount": amount,
                "source": effect.source,
                **effect.metadata,
            }
        )
        if target.hp <= 0:
            if (
                target.team == "dungeon"
                and source
                and self._maybe_revive_hollow(ctx, target, source)
            ):
                return followups
            target.alive = False
            target.hp = 0
            ctx.emit_text(f"{target.role} is defeated.")
            if target.team == "dungeon":
                ctx.add_reward(0.15)
                if source and source.team == "heroes":
                    source_stats = state.per_hero_stats.setdefault(
                        source.id, default_per_hero_stats(source)
                    )
                    source_stats["monsters_defeated"] = (
                        int(source_stats.get("monsters_defeated", 0)) + 1
                    )
                if source and target.equipment.get("boss"):
                    followups.append(BossDefeated(monster_id=target.id, source_id=source.id))
            if state.objective.carrier == target.id:
                if state.objective.fragile:
                    state.done = True
                    state.winner = "dungeon"
                    state.phase = "done"
                else:
                    state.objective.carrier = None
                    state.objective.pos = target.pos
                    target.inventory = [
                        item for item in target.inventory if item != state.objective.id
                    ]
        elif amount > 0 and target.team == "dungeon" and source and source.team == "heroes":
            followups.extend(self._boss_phase_followups(ctx, target, source))
        if (
            source
            and source.team == "dungeon"
            and source.role == "tusk_mauler"
            and amount > 0
            and effect.source != "cleave"
        ):
            adjacent = [
                hero
                for hero in state.heroes.values()
                if hero.id != target.id
                and hero.alive
                and self.runtime.grid.manhattan(source.pos, hero.pos) == 1
            ]
            if adjacent:
                cleave_target = min(adjacent, key=lambda h: h.hp)
                followups.append(
                    Damage(
                        source_id=source.id, target_id=cleave_target.id, amount=1, source="cleave"
                    )
                )
                state.trace.append(
                    {
                        "kind": "monster_cleave",
                        "round": state.round,
                        "monster_id": source.id,
                        "role": source.role,
                        "hero_id": cleave_target.id,
                        "primary_target": target.id,
                    }
                )
        return followups

    def _resolve_boss_phase_change(
        self, ctx: ResolverContext, effect: BossPhaseChange
    ) -> list[Effect]:
        monster = ctx.state.monsters.get(effect.monster_id)
        if not monster or not monster.equipment.get("boss"):
            return []
        triggered = set(str(item) for item in monster.equipment.get("triggered_phases", []))
        if effect.phase_id:
            triggered.add(effect.phase_id)
            monster.equipment["triggered_phases"] = sorted(triggered)
        payload = {
            "monster_id": monster.id,
            "role": monster.role,
            "boss_name": monster.equipment.get("boss_name", monster.role),
            "phase": effect.phase_id,
            "hp": monster.hp,
            **effect.payload_data,
        }
        ctx.state.trace.append({"kind": "boss_phase_changed", "round": ctx.state.round, **payload})
        if effect.message:
            ctx.state.event_log.append(effect.message)
            ctx.emit_text(effect.message)
        return self.runtime.emit_trigger(ctx, "on_boss_phase_changed", payload)

    def _resolve_boss_defeated(self, ctx: ResolverContext, effect: BossDefeated) -> list[Effect]:
        monster = ctx.state.monsters.get(effect.monster_id)
        if not monster or not monster.equipment.get("boss"):
            return []
        boss_name = str(monster.equipment.get("boss_name", monster.role))
        payload = {
            "monster_id": monster.id,
            "role": monster.role,
            "boss_name": boss_name,
            "source_id": effect.source_id,
        }
        ctx.state.trace.append({"kind": "boss_defeated", "round": ctx.state.round, **payload})
        ctx.state.event_log.append(f"Boss defeated: {boss_name}.")
        followups: list[Effect] = [
            UnlockAchievement(
                achievement_id=f"defeat_{monster.id}",
                title=f"Defeat {boss_name}",
                reward=float(monster.equipment.get("defeat_reward", 0.18)),
                layer="quest",
                description=str(
                    monster.equipment.get("defeat_description", f"Defeat {boss_name}.")
                ),
            )
        ]
        for raw in self._boss_raw_effects(monster, "on_defeated"):
            followups.extend(self.raw_effects(effect.source_id or ctx.actor_id, monster.id, raw))
        followups.extend(self.runtime.emit_trigger(ctx, "on_boss_defeated", payload))
        return followups

    def _resolve_cast_spell(self, ctx: ResolverContext, effect: CastSpell) -> list[Effect]:
        state = ctx.state
        caster = state.heroes.get(effect.caster_id)
        if not caster:
            return []
        spell = effect.spell or ("mend_wounds" if caster.role == "elf" else "spark_lance")
        if spell == "spark_lance":
            target = state.monsters.get(effect.target_id)
            if not target:
                return []
            hits = self.runtime.roll_successes(max(2, caster.focus // 2))
            blocks = self.runtime.roll_successes(target.guard)
            self._consume_spell_card(state, caster, spell, target_id=target.id)
            ctx.emit_text(
                f"{caster.role} casts spark lance at {target.role}: {hits} hits, {blocks} blocks."
            )
            return [
                Damage(
                    source_id=caster.id,
                    target_id=target.id,
                    amount=max(0, hits - blocks),
                    source="spell",
                    metadata={"spell": spell},
                )
            ]
        if spell == "mend_wounds":
            self._consume_spell_card(state, caster, spell, target_id=effect.target_id)
            return [Heal(target_id=effect.target_id, amount=2, source=spell)]
        if spell == "ward_circle":
            self._consume_spell_card(state, caster, spell, target_id=effect.target_id)
            return [ApplyStatus(target_id=effect.target_id, status="warded", source=spell)]
        if spell == "quiet_step":
            self._consume_spell_card(state, caster, spell, target_id=effect.target_id)
            return [ApplyStatus(target_id=effect.target_id, status="quiet_step", source=spell)]
        if spell == "blink_step":
            direction = effect.target_id
            dx, dy = DIRECTIONS[direction]
            landing = caster.pos
            for distance in (1, 2):
                candidate = (caster.pos[0] + dx * distance, caster.pos[1] + dy * distance)
                if self.runtime.grid.is_walkable(state, candidate):
                    landing = candidate
            self._consume_spell_card(state, caster, spell, target_id=direction)
            return [Move(entity_id=caster.id, to=landing, direction=f"blink {direction}")]
        if spell == "reveal_glyph":
            self._consume_spell_card(state, caster, spell, target_id=caster.id)
            return [SearchArea(actor_id=caster.id, category="glyphs")]
        if spell in {"hush_flame", "silence"}:
            self._consume_spell_card(state, caster, spell, target_id=caster.id)
            return [
                SetFlag(key="_alert_delta", value=-(2 if spell == "hush_flame" else 1)),
                EmitEvent(message=f"{caster.role} casts {spell}."),
            ]
        return []

    def _resolve_draw_card(self, ctx: ResolverContext, effect: DrawCard) -> list[Effect]:
        state = ctx.state
        deck = state.decks.get(effect.deck_id)
        if not deck:
            if self.runtime.deck_policy(state, effect.deck_id).get(
                "reshuffle"
            ) and state.discards.get(effect.deck_id):
                state.decks[effect.deck_id] = list(state.discards.get(effect.deck_id, []))
                self.runtime.rng.shuffle(state.decks[effect.deck_id])
                state.discards[effect.deck_id] = []
                state.trace.append(
                    {"kind": "deck_reshuffled", "round": state.round, "deck": effect.deck_id}
                )
                state.event_log.append(f"The {effect.deck_id} deck is reshuffled.")
                deck = state.decks.get(effect.deck_id)
            else:
                state.trace.append(
                    {"kind": "deck_exhausted", "round": state.round, "deck": effect.deck_id}
                )
                state.event_log.append(f"The {effect.deck_id} deck is exhausted.")
        if not deck:
            return []
        card = deck.pop(0)
        state.discards.setdefault(effect.deck_id, []).append(card)
        card_type = str(card.get("type", "treasure"))
        state.trace.append(
            {
                "kind": "card_draw",
                "round": state.round,
                "deck": effect.deck_id,
                "card": dict(card),
                "card_id": card.get("id"),
                "card_type": card_type,
                "rarity": card.get("rarity", "common"),
            }
        )
        if effect.deck_id == "treasure":
            self.runtime.increment_social_metric(state, "treasure_searches", effect.actor_id)
            if card_type in {"trap", "wandering_monster", "event"}:
                self.runtime.increment_social_metric(state, "bad_treasure_draws", effect.actor_id)
        ctx.emit_text(f"Draws {card.get('name', card.get('id', 'a card'))}.")
        state.event_log.append(
            f"Card drawn from {effect.deck_id}: {card.get('name', card.get('id', 'unknown card'))}."
        )
        followups = self._card_effects(effect.actor_id, effect.source_id, card)
        ctx.add_reward(float(card.get("reward", 0.05)))
        if card.get("dread"):
            followups.append(
                ModifyDread(
                    amount=int(card.get("dread", 0)),
                    reason=f"{effect.deck_id}:{card.get('id', card_type)}",
                )
            )
        followups.extend(
            self.runtime.emit_trigger(
                ctx, "on_card_drawn", {"deck": effect.deck_id, "card": dict(card)}
            )
        )
        return followups

    def _card_effects(self, actor_id: str, source_id: str, card: dict[str, Any]) -> list[Effect]:
        effects: list[Effect] = []
        raw_effects = list(card.get("effects", [])) if isinstance(card.get("effects"), list) else []
        card_type = str(card.get("type", "treasure"))
        item = card.get("item")
        if item:
            if card_type == "spell":
                raw_effects.append({"type": "spell", "item": item})
            elif card_type == "armor":
                raw_effects.append({"type": "armor", "item": item})
            elif card_type in {"weapon", "artifact", "healing"}:
                raw_effects.append({"type": card_type, "item": item})
            elif card_type != "event":
                raw_effects.append({"type": "item", "item": item})
        if "treasure" in card:
            raw_effects.append({"type": "gold", "amount": card.get("treasure", 1)})
        if "alert" in card:
            raw_effects.append({"type": "alert", "amount": card.get("alert", 1)})
        if "damage" in card:
            raw_effects.append({"type": "damage", "amount": card.get("damage", 1)})
        if "heal" in card:
            raw_effects.append({"type": "heal", "amount": card.get("heal")})
        if isinstance(card.get("spawn"), dict):
            spawn = dict(card["spawn"])
            role = str(spawn.get("role", "skitterling"))
            if spawn.get("near") == "searching_hero":
                raw_effects.append(
                    {"type": "spawn_monster_near", "role": role, "anchor_id": actor_id}
                )
            else:
                raw_effects.append({"type": "spawn_monster", **spawn})
        if card_type == "wandering_monster" and not card.get("spawn"):
            raw_effects.append(
                {"type": "spawn_monster_near", "role": "skitterling", "anchor_id": actor_id}
            )
        if not raw_effects and card_type == "healing":
            raw_effects.append({"type": "item", "item": "healing_draught"})
        effects.extend(self.raw_effects(actor_id, source_id, raw_effects))
        if card_type == "wandering_monster":
            effects.append(IncrementCounter(key="_social:wanderers_spawned_by_greed", amount=1))
        return effects

    def _resolve_spawn_monster(self, ctx: ResolverContext, effect: SpawnMonster) -> list[Effect]:
        state = ctx.state
        if effect.role not in MONSTER_TYPES:
            return []
        monster_id = (
            effect.monster_id
            or f"{effect.role}_{len([m for m in state.monsters if m.startswith(effect.role + '_')]) + 1}"
        )
        if monster_id in state.monsters:
            return []
        pos = effect.pos or self.runtime.nearest_free_adjacent(
            state, state.heroes.get(ctx.actor_id, next(iter(state.heroes.values()))).pos
        )
        if not pos:
            return []
        spec = MONSTER_TYPES[effect.role]
        state.monsters[monster_id] = Entity(
            id=monster_id,
            team="dungeon",
            role=effect.role,
            hp=spec["hp"],
            max_hp=spec["hp"],
            attack=spec["attack"],
            guard=spec["guard"],
            speed=spec["speed"],
            behavior=spec["behavior"],
            pos=pos,
            activation=effect.activation,
            room_id=self.runtime.grid.room_id_at(state.rooms, pos),
            sight_range=int(spec.get("sight_range", 6)),
            equipment={key: spec[key] for key in ("attack_range",) if key in spec},
            status=list(effect.status),
        )
        ctx.emit_text(f"{effect.role} appears.")
        return []

    def _resolve_spawn_monster_near(
        self, ctx: ResolverContext, effect: SpawnMonsterNear
    ) -> list[Effect]:
        anchor = ctx.state.all_entities().get(effect.anchor_id)
        pos = None
        if anchor:
            pos = self.runtime.nearest_free_adjacent(ctx.state, anchor.pos)
        pos = pos or effect.fallback_pos
        return [
            SpawnMonster(
                monster_id=effect.monster_id,
                role=effect.role,
                pos=pos,
                activation=effect.activation,
                status=list(effect.status),
            )
        ]

    def _resolve_equip_item(self, ctx: ResolverContext, effect: EquipItem) -> list[Effect]:
        hero = ctx.state.heroes.get(effect.actor_id)
        if not hero or effect.item_id not in hero.inventory:
            return []
        slot = self.runtime.item_slot(effect.item_id)
        previous = hero.equipment.get(slot)
        if (
            previous
            and self.runtime.is_equippable(str(previous))
            and previous not in hero.inventory
        ):
            hero.inventory.append(str(previous))
        hero.inventory.remove(effect.item_id)
        hero.equipment[slot] = effect.item_id
        self.runtime.refresh_equipment_stats(hero)
        event = {
            "kind": "item_equipped",
            "round": ctx.state.round,
            "agent_id": hero.id,
            "role": hero.role,
            "item": effect.item_id,
            "slot": slot,
            "item_type": "weapon" if effect.item_id in WEAPON_ITEMS else "armor",
        }
        ctx.state.trace.append(event)
        if effect.item_id in ARMOR_ITEMS:
            ctx.state.trace.append({**event, "kind": "armor_equipped"})
        ctx.emit_text(f"{hero.role} equips {self.runtime.item_name(effect.item_id)}.")
        ctx.add_reward(0.04)
        return []

    def _resolve_disarm(self, ctx: ResolverContext, effect: DisarmTrap) -> list[Effect]:
        hero = ctx.state.heroes[effect.actor_id]
        trap = ctx.state.traps[effect.trap_id]
        roll = self.runtime.rng.randint(1, 6) + (2 if hero.role == "dwarf" else 0)
        trap.revealed = True
        trap.armed = False
        if roll >= 4:
            if "specialist" in str(hero.equipment.get("combat_role", "")) or hero.role == "dwarf":
                specialist_actions = ctx.state.social_metrics.setdefault("specialist_actions", {})
                key = f"{hero.role}_disarm"
                specialist_actions[key] = int(specialist_actions.get(key, 0)) + 1
                stats = ctx.state.per_hero_stats.setdefault(
                    hero.id, default_per_hero_stats(hero)
                )
                stats["specialist_actions"] = int(stats.get("specialist_actions", 0)) + 1
            ctx.add_reward(0.08)
            ctx.emit_text(f"{hero.role} disarms {trap.id}.")
            return []
        ctx.emit_text(f"{hero.role} fails to disarm {trap.id}; it triggers.")
        return [Damage(source_id=trap.id, target_id=hero.id, amount=1, source="trap")]

    def _resolve_open_chest(self, ctx: ResolverContext, effect: OpenChest) -> list[Effect]:
        chest = ctx.state.chests[effect.chest_id]
        chest.opened = True
        ctx.state.trace.append(
            {
                "kind": "search",
                "round": ctx.state.round,
                "agent_id": effect.actor_id,
                "category": "treasure",
                "found": [chest.id],
            }
        )
        ctx.emit_text(f"{ctx.state.heroes[effect.actor_id].role} searches a chest.")
        return self._contents_effects(effect.actor_id, chest.contents)

    def _contents_effects(self, actor_id: str, contents: Any) -> list[Effect]:
        if isinstance(contents, list):
            effects: list[Effect] = []
            for item in contents:
                effects.extend(self._contents_effects(actor_id, item))
            return effects
        if isinstance(contents, dict):
            payload_type = str(contents.get("type", "item"))
            if payload_type == "table":
                entries = list(contents.get("entries", []))
                return (
                    self._contents_effects(actor_id, self.runtime.rng.choice(entries))
                    if entries
                    else []
                )
            if payload_type == "bundle":
                return self._contents_effects(actor_id, list(contents.get("contents", [])))
            if payload_type == "draw_deck":
                return [
                    DrawCard(
                        actor_id=actor_id,
                        deck_id=str(contents.get("deck", "treasure")),
                        source_id="chest",
                    )
                ]
            return self.raw_effects(actor_id, "chest", contents)
        if contents in {"coin_cache", "treasure"}:
            return [
                AddInventory(target_id=actor_id, item_id="coin_cache"),
                SetFlag(key="_treasure_delta", value=1),
            ]
        if contents == "ambush":
            return [SpawnMonster(role="skitterling")]
        if isinstance(contents, str) and contents:
            return [AddInventory(target_id=actor_id, item_id=contents)]
        return []

    def _resolve_search_furniture(
        self, ctx: ResolverContext, effect: SearchFurniture
    ) -> list[Effect]:
        furniture = ctx.state.furniture[effect.furniture_id]
        category = "interact" if effect.via_interact else effect.category
        furniture.searched_categories.add(category)
        furniture.searched = bool(furniture.searched_categories)
        raw = furniture.search_effects.get(effect.category)
        if raw is None:
            raw = {"type": "draw_deck", "deck": furniture.deck or "treasure"}
        event = self._record_furniture_event(
            ctx,
            "furniture_searched",
            furniture,
            effect.category,
            {"trigger": f"search_{effect.category}"},
        )
        ctx.info["furniture_result"] = event
        ctx.state.scripts["_last_furniture_result"] = event
        ctx.state.trace.append(
            {
                "kind": "search",
                "round": ctx.state.round,
                "agent_id": effect.actor_id,
                "role": ctx.state.heroes[effect.actor_id].role,
                "category": effect.category,
                "found": [furniture.id],
            }
        )
        ctx.emit_text(f"{ctx.state.heroes[effect.actor_id].role} searches {furniture.name}.")
        return [
            *self.raw_effects(effect.actor_id, furniture.id, raw),
            *self.runtime.emit_trigger(ctx, "on_furniture_searched", event),
        ]

    def _resolve_damage_furniture(
        self, ctx: ResolverContext, effect: DamageFurniture
    ) -> list[Effect]:
        furniture = ctx.state.furniture[effect.furniture_id]
        furniture.hp = max(0, furniture.hp - max(1, effect.amount))
        result: dict[str, Any] = {"damage": max(1, effect.amount), "destroyed": False}
        followups: list[Effect] = []
        if furniture.hp <= 0 and not furniture.destroyed:
            furniture.destroyed = True
            result["destroyed"] = True
            followups.extend(
                self.raw_effects(effect.actor_id, furniture.id, furniture.break_effect)
            )
        event = self._record_furniture_event(
            ctx,
            "furniture_destroyed" if furniture.destroyed else "furniture_damaged",
            furniture,
            "destroy",
            result,
        )
        ctx.info["furniture_result"] = event
        ctx.state.scripts["_last_furniture_result"] = event
        ctx.emit_text(f"{ctx.state.heroes[effect.actor_id].role} strikes {furniture.name}.")
        ctx.add_reward(0.02 * max(1, effect.amount) + (0.05 if furniture.destroyed else 0.0))
        if furniture.destroyed:
            followups.extend(self.runtime.emit_trigger(ctx, "on_furniture_destroyed", event))
        return followups

    def _resolve_search_area(self, ctx: ResolverContext, effect: SearchArea) -> list[Effect]:
        state = ctx.state
        hero = state.heroes[effect.actor_id]
        visible = self.runtime.grid.visible_tiles(state, hero.id)
        if effect.category == "glyphs":
            visible = visible | {hero.pos, *self.runtime.grid.adjacent_positions(hero.pos)}
        followups: list[Effect] = []
        found: list[str] = []
        if effect.category == "tile" and effect.pos is not None:
            for trap in state.traps.values():
                if trap.pos == effect.pos and trap.armed and not trap.revealed:
                    followups.append(RevealTrap(trap_id=trap.id))
                    found.append(trap.id)
            for door in state.doors.values():
                if door.pos == effect.pos and door.secret and not door.discovered:
                    followups.append(RevealSecretDoor(door_id=door.id))
                    found.append(door.id)
        if effect.category in {"traps", "glyphs"}:
            for trap in state.traps.values():
                if trap.pos in visible and trap.armed and not trap.revealed:
                    followups.append(RevealTrap(trap_id=trap.id))
                    found.append(trap.id)
        if effect.category in {"secrets", "glyphs"}:
            for door in state.doors.values():
                if door.pos in visible and door.secret and not door.discovered:
                    followups.append(RevealSecretDoor(door_id=door.id))
                    found.append(door.id)
        if effect.category == "glyphs":
            for furniture in state.furniture.values():
                if furniture.pos in visible and not furniture.visible:
                    furniture.visible = True
                    found.append(furniture.id)
        state.trace.append(
            {
                "kind": "search",
                "round": state.round,
                "agent_id": hero.id,
                "role": hero.role,
                "category": effect.category,
                "found": list(found),
            }
        )
        ctx.emit_text(
            f"{hero.role} searches {effect.category}: {', '.join(found) if found else 'nothing found'}."
        )
        ctx.add_reward(0.06 * len(found))
        return followups

    def _resolve_use_item(self, ctx: ResolverContext, effect: UseItem) -> list[Effect]:
        hero = ctx.state.heroes[effect.actor_id]
        if effect.item_id == "healing_draught" and effect.item_id in hero.inventory:
            hero.inventory.remove(effect.item_id)
            return [Heal(target_id=hero.id, amount=3, source="healing_draught")]
        if effect.item_id == "lantern_lens" and effect.item_id in hero.inventory:
            if "lantern_lens_active" not in hero.status:
                hero.status.append("lantern_lens_active")
            ctx.state.torch = min(24, ctx.state.torch + 2)
            ctx.emit_text(f"{hero.role} raises the lantern lens; the party's light steadies.")
            ctx.add_reward(0.06)
        return []

    def _resolve_monster_act(self, ctx: ResolverContext, effect: MonsterAct) -> list[Effect]:
        state = ctx.state
        monster = state.monsters.get(effect.monster_id)
        if not monster or not monster.alive:
            return []
        heroes = [h for h in state.heroes.values() if h.alive]
        if not heroes:
            return []
        adjacent = [h for h in heroes if self.runtime.grid.manhattan(monster.pos, h.pos) == 1]
        if adjacent:
            monster.activation = "engaged"
            target = min(adjacent, key=lambda h: h.hp)
            return [AttackRoll(attacker_id=monster.id, target_id=target.id)]
        visible_targets = [
            h
            for h in heroes
            if self.runtime.grid.manhattan(monster.pos, h.pos) <= monster.sight_range
            and self.runtime.grid.line_clear(state, monster.pos, h.pos)
        ]
        if monster.role == "cinder_mage" and visible_targets:
            attack_range = int(monster.equipment.get("attack_range", 5))
            ranged_targets = [
                h
                for h in visible_targets
                if self.runtime.grid.manhattan(monster.pos, h.pos) <= attack_range
            ]
            if ranged_targets:
                monster.activation = "engaged"
                target = min(
                    ranged_targets,
                    key=lambda h: (h.hp, self.runtime.grid.manhattan(monster.pos, h.pos)),
                )
                return [
                    AttackRoll(attacker_id=monster.id, target_id=target.id, ranged=True),
                    SetFlag(key="_alert_delta", value=1),
                ]
        target = (
            state.heroes.get(state.objective.carrier)
            if monster.behavior == "hunt_objective_carrier"
            and state.objective.carrier in state.heroes
            else None
        )
        target = target or min(
            visible_targets or heroes, key=lambda h: self.runtime.grid.manhattan(monster.pos, h.pos)
        )
        path = self.runtime.grid.find_path(state, monster.pos, target.pos, ignore_entities=True)
        if len(path) > 1:
            old = monster.pos
            steps = min(monster.speed, max(1, len(path) - 2))
            for candidate in path[1 : 1 + steps]:
                if state.entity_at(candidate):
                    break
                monster.pos = candidate
            if monster.pos != old:
                ctx.emit_text(f"{monster.role} advances toward {target.role}.")
        return []

    def _hero_damage_prevention(
        self, ctx: ResolverContext, hero: Entity, damage: int, *, source_id: str
    ) -> int:
        if damage <= 0:
            return damage
        if "quiet_step" in hero.status:
            hero.status.remove("quiet_step")
            reduced = max(0, damage - 1)
            self._record_spell_status(
                ctx.state, hero, "quiet_step", "monster_pressure", damage - reduced, source_id
            )
            return reduced
        if "warded" in hero.status:
            hero.status.remove("warded")
            reduced = max(0, damage - 1)
            self._record_spell_status(
                ctx.state, hero, "ward_circle", "incoming_damage", damage - reduced, source_id
            )
            return reduced
        if hero.equipment.get("helm") == "iron_helm" and damage >= hero.hp:
            hero.equipment.pop("helm", None)
            self.runtime.refresh_equipment_stats(hero)
            ctx.state.trace.append(
                {
                    "kind": "defensive_prevention",
                    "round": ctx.state.round,
                    "agent_id": hero.id,
                    "role": hero.role,
                    "item": "iron_helm",
                    "prevented": "lethal_hit",
                    "prevented_damage": 1,
                }
            )
            ctx.state.event_log.append(f"{hero.role}'s iron helm turns a lethal blow.")
            return max(0, hero.hp - 1)
        return damage

    def _monster_damage_prevention(
        self, ctx: ResolverContext, attacker: Entity, monster: Entity, damage: int
    ) -> int:
        if damage <= 0:
            return damage
        if monster.role == "mirror_adept" and "mirror_decoy_spent" not in monster.status:
            monster.status.append("mirror_decoy_spent")
            ctx.state.trace.append(
                {
                    "kind": "monster_decoy_triggered",
                    "round": ctx.state.round,
                    "monster_id": monster.id,
                    "role": monster.role,
                    "hero_id": attacker.id,
                    "prevented_damage": damage,
                }
            )
            ctx.state.trace.append(
                {
                    "kind": "monster_special_used",
                    "round": ctx.state.round,
                    "monster_id": monster.id,
                    "role": monster.role,
                    "special": "decoy_triggered",
                    "hero_id": attacker.id,
                }
            )
            ctx.state.event_log.append(f"{monster.role}'s decoy absorbs {attacker.role}'s blow.")
            return 0
        gate = self._boss_damage_gate(monster)
        counter_flags = [str(item) for item in gate.get("counter_flags", [])]
        if not counter_flags and gate.get("counter_flag"):
            counter_flags = [str(gate["counter_flag"])]
        max_without_counter = gate.get("max_damage_without_counter")
        counter_ready = any(ctx.state.scripts.get(flag) for flag in counter_flags)
        if counter_flags and not counter_ready and max_without_counter is not None:
            capped = min(damage, int(max_without_counter))
            if capped < damage:
                message = str(
                    gate.get("message")
                    or f"{monster.role}'s boss ward turns aside the worst of the hit."
                )
                ctx.state.trace.append(
                    {
                        "kind": "boss_special_used",
                        "round": ctx.state.round,
                        "monster_id": monster.id,
                        "role": monster.role,
                        "boss_name": monster.equipment.get("boss_name", monster.role),
                        "special": "counter_required",
                        "counter_flags": counter_flags,
                        "prevented_damage": damage - capped,
                        "attacker_id": attacker.id,
                    }
                )
                ctx.state.event_log.append(message)
            return capped
        return damage

    def _boss_phase_followups(
        self, ctx: ResolverContext, monster: Entity, attacker: Entity
    ) -> list[Effect]:
        if not monster.equipment.get("boss"):
            return []
        phases = monster.equipment.get("phases")
        if not isinstance(phases, list):
            return []
        triggered = set(str(item) for item in monster.equipment.get("triggered_phases", []))
        followups: list[Effect] = []
        for phase in phases:
            if not isinstance(phase, dict):
                continue
            phase_id = str(phase.get("id") or phase.get("phase") or "")
            threshold = int(phase.get("hp_at_or_below", phase.get("threshold", -1)))
            if not phase_id or phase_id in triggered or threshold < 0 or monster.hp > threshold:
                continue
            if "attack_bonus" in phase:
                monster.equipment["phase_attack_bonus"] = int(
                    monster.equipment.get("phase_attack_bonus", 0)
                ) + int(phase["attack_bonus"])
            if "alert" in phase:
                followups.append(SetFlag(key="_alert_delta", value=int(phase["alert"])))
            if isinstance(phase.get("set_script"), dict):
                for key, value in phase["set_script"].items():
                    followups.append(SetFlag(key=str(key), value=value))
            for status in phase.get("status", []):
                followups.append(
                    ApplyStatus(target_id=monster.id, status=str(status), source="boss_phase")
                )
            for raw in phase.get("effects", []):
                followups.extend(self.raw_effects(attacker.id, monster.id, raw))
            message = str(phase.get("message") or f"{monster.role} enters {phase_id}.")
            followups.append(
                BossPhaseChange(
                    monster_id=monster.id,
                    phase_id=phase_id,
                    message=message,
                    payload_data={"attacker_id": attacker.id},
                )
            )
        return followups

    def _boss_damage_gate(self, monster: Entity) -> dict[str, Any]:
        if not monster.equipment.get("boss"):
            return {}
        gate = monster.equipment.get("damage_gate")
        data = dict(gate) if isinstance(gate, dict) else {}
        if "counter_flag" not in data and monster.equipment.get("counter_flag"):
            data["counter_flag"] = monster.equipment["counter_flag"]
        if (
            "max_damage_without_counter" not in data
            and monster.equipment.get("max_damage_without_counter") is not None
        ):
            data["max_damage_without_counter"] = monster.equipment["max_damage_without_counter"]
        return data

    def _boss_raw_effects(self, monster: Entity, key: str) -> list[Any]:
        raw = monster.equipment.get(key, [])
        if isinstance(raw, list):
            return raw
        if raw:
            return [raw]
        return []

    def _maybe_revive_hollow(self, ctx: ResolverContext, monster: Entity, attacker: Entity) -> bool:
        if monster.role != "hollow_knight":
            return False
        if attacker.equipment.get("charm") == "holy_charm":
            if "banished" not in monster.status:
                monster.status.append("banished")
            ctx.state.trace.append(
                {
                    "kind": "defensive_prevention",
                    "round": ctx.state.round,
                    "agent_id": attacker.id,
                    "role": attacker.role,
                    "item": "holy_charm",
                    "prevented": "hollow_revive",
                    "monster_id": monster.id,
                    "monster_role": monster.role,
                }
            )
            ctx.state.event_log.append(f"{attacker.role}'s holy charm stills {monster.role}.")
            return False
        if "revived" in monster.status or {"banished", "vulnerable", "hollow_banished"} & set(
            monster.status
        ):
            return False
        if ctx.state.scripts.get(f"{monster.id}_banished") or ctx.state.scripts.get(
            "hollow_knight_banished"
        ):
            return False
        monster.status.append("revived")
        monster.alive = True
        monster.hp = 1
        ctx.state.trace.append(
            {
                "kind": "monster_revived",
                "round": ctx.state.round,
                "monster_id": monster.id,
                "role": monster.role,
                "hero_id": attacker.id,
                "restored_hp": 1,
            }
        )
        ctx.state.trace.append(
            {
                "kind": "monster_special_used",
                "round": ctx.state.round,
                "monster_id": monster.id,
                "role": monster.role,
                "special": "revived",
                "hero_id": attacker.id,
            }
        )
        ctx.state.event_log.append(f"{monster.role} rises again.")
        return True

    def _record_spell_status(
        self,
        state: GameState,
        hero: Entity,
        spell: str,
        trigger: str,
        prevented: int,
        source_id: str,
    ) -> None:
        state.trace.append(
            {
                "kind": "spell_status_triggered",
                "round": state.round,
                "agent_id": hero.id,
                "role": hero.role,
                "spell": spell,
                "trigger": trigger,
                "prevented_damage": prevented,
                "source_id": source_id,
            }
        )
        state.event_log.append(f"{hero.role}'s {spell} triggers.")

    def _record_furniture_event(
        self,
        ctx: ResolverContext,
        kind: str,
        furniture: Any,
        category: str,
        effect_result: dict[str, Any],
    ) -> dict[str, Any]:
        hero = ctx.state.heroes[ctx.actor_id]
        event = {
            "kind": kind,
            "round": ctx.state.round,
            "agent_id": hero.id,
            "role": hero.role,
            "furniture_id": furniture.id,
            "furniture_name": furniture.name,
            "category": category,
            "hp": furniture.hp,
            "max_hp": furniture.max_hp,
            "destroyed": furniture.destroyed,
            "effect_result": effect_result,
        }
        ctx.state.trace.append(event)
        ctx.state.event_log.append(f"{hero.role} {category} {furniture.name}.")
        return event

    def _script_effects(self, ctx: ResolverContext, script_name: str) -> list[Effect]:
        script = ctx.state.scripts.get(script_name)
        if not isinstance(script, dict):
            return []
        effects: list[Effect] = []
        if script.get("message"):
            effects.append(EmitEvent(message=str(script["message"])))
        for raw in script.get("effects", []):
            effects.extend(self.raw_effects(ctx.actor_id, script_name, raw))
        return effects

    def _consume_spell_card(
        self, state: GameState, hero: Entity, spell: str, *, target_id: str
    ) -> None:
        spec = SPELL_CARDS.get(spell, {})
        if not spec.get("reusable", False):
            used = list(hero.equipment.get("used_spell_cards", []))
            used.append(spell)
            hero.equipment["used_spell_cards"] = used
        state.trace.append(
            {
                "kind": "spell_used",
                "round": state.round,
                "agent_id": hero.id,
                "role": hero.role,
                "spell": spell,
                "school": spec.get("school"),
                "target": target_id,
            }
        )
        state.event_log.append(f"{hero.role} casts {spell}.")

    def _effect_record(self, effect: Effect) -> dict[str, Any]:
        def stable(value: Any) -> Any:
            if isinstance(value, Enum):
                return value.value
            if isinstance(value, tuple):
                return [stable(item) for item in value]
            if isinstance(value, list):
                return [stable(item) for item in value]
            if isinstance(value, dict):
                return {str(key): stable(item) for key, item in value.items()}
            return value

        data = asdict(effect) if is_dataclass(effect) else {"kind": type(effect).__name__}
        data = stable(data)
        data["kind"] = type(effect).__name__
        return data


class PhaseController:
    """Owns phase, turn, round, cleanup, and done transitions."""

    def __init__(self, runtime: EngineRuntime) -> None:
        self.runtime = runtime

    def start_hero_turn(self, state: GameState, hero_id: str) -> None:
        hero = state.heroes.get(hero_id)
        if not hero or not hero.alive or hero.id in state.extracted_heroes:
            return
        state.major_action_used[hero.id] = False
        if self.runtime.ruleset_enabled(state, "roll_to_move"):
            spec = state.ruleset.get("roll_to_move", {})
            dice = [int(side) for side in spec.get("dice", [6, 6])]
            roll = sum(self.runtime.rng.randint(1, max(1, side)) for side in dice)
            roll = max(int(spec.get("minimum", 0)), roll)
            state.movement_rolls[hero.id] = roll
            state.movement_remaining[hero.id] = roll
            state.trace.append(
                {
                    "kind": "movement_roll",
                    "round": state.round,
                    "agent_id": hero.id,
                    "role": hero.role,
                    "roll": roll,
                    "dice": dice,
                }
            )
        else:
            state.movement_rolls[hero.id] = 0
            state.movement_remaining[hero.id] = 0

    def advance(self, state: GameState, target: Phase, ctx: ResolverContext | None = None) -> None:
        if target == Phase.DONE:
            state.phase = "done"
            state.done = True
        elif target == Phase.WARDEN_TURN:
            state.phase = "warden"
            state.turn_index = 0
        elif target == Phase.HERO_TURN:
            state.phase = "hero"
        elif target == Phase.CLEANUP:
            self.end_warden_phase(state, ctx)

    def finish_action(self, state: GameState, agent_id: str, action_type: str) -> None:
        self.check_end_conditions(state)
        if state.done:
            return
        if state.phase != "hero" or agent_id not in state.heroes:
            return
        if (
            action_type == "end_turn"
            or (
                self.runtime.classic_enabled(state)
                and state.major_action_used.get(agent_id)
                and state.movement_remaining.get(agent_id, 0) <= 0
            )
            or state.ap_remaining.get(agent_id, 0) <= 0
        ):
            self.advance_hero_turn(state)

    def end_warden_phase(self, state: GameState, ctx: ResolverContext | None = None) -> None:
        if state.done:
            return
        local_ctx = ctx or ResolverContext(
            state=state,
            runtime=self.runtime,
            actor_id=state.active_agent(),
            action={"type": "warden_cleanup"},
        )
        reactions = self.runtime.emit_trigger(
            local_ctx, "on_warden_cleanup", {"round": state.round}
        )
        if reactions:
            before_effect_count = len(local_ctx.resolved_effects)
            self.runtime.resolver.resolve_many(local_ctx, reactions)
            state.trace.append(
                {
                    "kind": "phase_trigger_resolution",
                    "round": state.round,
                    "trigger_name": "on_warden_cleanup",
                    "resolved_effects": list(local_ctx.resolved_effects[before_effect_count:]),
                    "triggered_reactions": list(local_ctx.triggered_reactions),
                    "narration": " ".join(local_ctx.texts).strip(),
                    "reward": round(local_ctx.reward, 4),
                }
            )
        self._record_round_social_metrics(state)
        state.round += 1
        state.torch = max(0, state.torch - 1)
        state.phase = "hero"
        state.turn_index = 0
        for hero_id, hero in state.heroes.items():
            state.ap_remaining[hero_id] = (
                3 if hero.alive and hero_id not in state.extracted_heroes else 0
            )
            if "guarded" in hero.status:
                hero.status.remove("guarded")
        self.skip_downed_heroes(state)
        if state.phase == "hero":
            self.start_hero_turn(state, state.active_agent())
        self.runtime.run_script(state, "end_phase")
        self.check_end_conditions(state)

    def _record_round_social_metrics(self, state: GameState) -> None:
        living = [hero for hero in state.living_heroes() if hero.id not in state.extracted_heroes]
        if len(living) >= 2:
            max_distance = max(
                self.runtime.grid.manhattan(left.pos, right.pos)
                for index, left in enumerate(living)
                for right in living[index + 1 :]
            )
            if max_distance >= 8:
                self.runtime.increment_social_metric(state, "split_party_rounds")
        for hero in living:
            if hero.pos in self.runtime.grid.adjacent_positions(state.escape_tile):
                blockers = [
                    ally
                    for ally in living
                    if ally.id != hero.id and self.runtime.grid.manhattan(hero.pos, ally.pos) == 1
                ]
                if blockers:
                    self.runtime.increment_social_metric(state, "body_blocked_ally_escape")
            if "guarded" in hero.status and any(
                door.pos in self.runtime.grid.adjacent_positions(hero.pos)
                for door in state.doors.values()
            ):
                self.runtime.increment_social_metric(state, "doorway_hold_turns")

    def advance_hero_turn(self, state: GameState) -> None:
        if state.done:
            return
        state.turn_index += 1
        self.skip_downed_heroes(state)
        if state.turn_index >= len(state.hero_order):
            state.phase = "warden"
            state.turn_index = 0
        elif state.phase == "hero":
            self.start_hero_turn(state, state.active_agent())

    def skip_downed_heroes(self, state: GameState) -> None:
        while state.phase == "hero" and state.turn_index < len(state.hero_order):
            hero_id = state.hero_order[state.turn_index]
            if state.heroes[hero_id].alive and hero_id not in state.extracted_heroes:
                break
            state.turn_index += 1
        if state.phase == "hero" and state.turn_index >= len(state.hero_order):
            state.phase = "warden"
            state.turn_index = 0

    def check_end_conditions(self, state: GameState) -> None:
        if state.done:
            state.phase = "done"
            return
        if not state.living_heroes():
            state.done = True
            state.winner = "dungeon"
            state.phase = "done"
            state.termination_reason = state.termination_reason or "party_defeated"
            return
        living_unextracted = [
            hero for hero in state.living_heroes() if hero.id not in state.extracted_heroes
        ]
        if state.objective.recovered and not living_unextracted:
            state.done = True
            state.winner = "heroes"
            state.phase = "done"
            state.termination_reason = "full_party_extraction"
            return
        if state.objective.recovered and not self.runtime.ruleset_enabled(state, "extraction"):
            state.done = True
            state.winner = "heroes"
            state.phase = "done"
            state.termination_reason = "objective_escaped"


class ActionTranslator:
    """Converts validated action dictionaries into typed effect lists."""

    def __init__(self, runtime: EngineRuntime) -> None:
        self.runtime = runtime

    def translate(self, state: GameState, agent_id: str, action: dict[str, Any]) -> list[Effect]:
        action_type = str(action.get("type"))
        if agent_id == "warden":
            if action_type == "warden_auto":
                return [
                    *self.runtime.deterministic_warden_dread_effects(state),
                    *[
                        MonsterAct(monster_id=monster_id, timing=Timing.WARDEN)
                        for monster_id, monster in state.monsters.items()
                        if monster.alive and monster.activation != "dormant"
                    ],
                    AdvancePhase(target=Phase.CLEANUP),
                ]
            if action_type == "activate_monster":
                return [MonsterAct(monster_id=str(action.get("target")), timing=Timing.WARDEN)]
            if action_type == "warden_spend_dread":
                payload = action.get("payload") if isinstance(action.get("payload"), dict) else {}
                return [
                    WardenSpendDread(
                        effect=str(payload.get("effect", "spawn_wanderer")),
                        target_id=str(action.get("target", "")),
                        cost=int(payload.get("cost", 1)),
                    )
                ]
            if action_type == "end_turn":
                return [AdvancePhase(target=Phase.CLEANUP)]
        hero = state.heroes[agent_id]
        effects: list[Effect] = []
        if action_type != "end_turn":
            ap_cost = (
                0
                if self.runtime.classic_enabled(state) and action_type == "move"
                else ACTION_COSTS.get(action_type, 0)
            )
            effects.append(PayAP(entity_id=hero.id, action_type=action_type, amount=ap_cost))
            if self.runtime.classic_enabled(state) and self.runtime.is_major_action(
                state, action_type
            ):
                effects.append(MarkMajorAction(entity_id=hero.id, action_type=action_type))
        if action_type == "move":
            direction = str(action.get("direction"))
            dx, dy = DIRECTIONS[direction]
            if self.runtime.classic_enabled(state):
                effects.append(SpendMovement(entity_id=hero.id, amount=1))
            effects.append(
                Move(
                    entity_id=hero.id, to=(hero.pos[0] + dx, hero.pos[1] + dy), direction=direction
                )
            )
        elif action_type == "open_door":
            effects.append(OpenDoor(actor_id=hero.id, door_id=str(action.get("target"))))
        elif action_type in {"attack_melee", "attack_ranged"}:
            effects.append(
                AttackRoll(
                    attacker_id=hero.id,
                    target_id=str(action.get("target")),
                    ranged=action_type == "attack_ranged",
                )
            )
        elif action_type == "cast":
            effects.append(
                CastSpell(
                    caster_id=hero.id,
                    spell=str((action.get("payload") or {}).get("spell", "")),
                    target_id=str(action.get("target")),
                )
            )
        elif action_type == "inspect_tile":
            effects.append(
                SearchArea(
                    actor_id=hero.id,
                    category="tile",
                    pos=self.runtime.pos_from_target(action.get("target"), hero.pos),
                )
            )
        elif action_type == "inspect_room":
            effects.append(SearchArea(actor_id=hero.id, category="glyphs"))
        elif action_type == "search_traps":
            effects.append(SearchArea(actor_id=hero.id, category="traps"))
        elif action_type == "search_secrets":
            effects.append(SearchArea(actor_id=hero.id, category="secrets"))
        elif action_type == "search_treasure":
            target = str(action.get("target"))
            effects.append(
                OpenChest(actor_id=hero.id, chest_id=target)
                if target in state.chests
                else SearchFurniture(actor_id=hero.id, furniture_id=target, category="treasure")
            )
        elif action_type == "search_furniture":
            effects.append(
                SearchFurniture(
                    actor_id=hero.id, furniture_id=str(action.get("target")), category="furniture"
                )
            )
        elif action_type == "attack_object":
            attack_dice = self.runtime.attack_dice(hero, ranged=False)
            effects.append(
                DamageFurniture(
                    actor_id=hero.id,
                    furniture_id=str(action.get("target")),
                    amount=max(1, self.runtime.roll_successes(attack_dice)),
                )
            )
        elif action_type == "disarm":
            effects.append(DisarmTrap(actor_id=hero.id, trap_id=str(action.get("target"))))
        elif action_type == "interact":
            target = str(action.get("target"))
            if target == "escape":
                effects.append(
                    ExtractHero(actor_id=hero.id, with_objective=state.objective.carrier == hero.id)
                )
            elif target == state.objective.id:
                effects.append(ObjectiveTake(actor_id=hero.id))
            elif target in state.chests:
                effects.append(OpenChest(actor_id=hero.id, chest_id=target))
            elif target in state.furniture:
                effects.append(
                    SearchFurniture(
                        actor_id=hero.id,
                        furniture_id=target,
                        category="furniture",
                        via_interact=True,
                    )
                )
        elif action_type == "use_item":
            effects.append(UseItem(actor_id=hero.id, item_id=str(action.get("target"))))
        elif action_type == "equip_item":
            effects.append(EquipItem(actor_id=hero.id, item_id=str(action.get("target"))))
        elif action_type == "give_item":
            effects.append(
                TransferItem(
                    source_id=hero.id,
                    target_id=str(action.get("target")),
                    item_id=str((action.get("payload") or {}).get("item", "")),
                )
            )
        elif action_type == "message":
            payload = action.get("payload") if isinstance(action.get("payload"), dict) else {}
            text = str(
                payload.get("text")
                or payload.get("message")
                or ""
            ).strip()
            text = " ".join(text.split())[:240] or "(no message)"
            effects.append(
                MessageEffect(
                    actor_id=hero.id,
                    target=str(action.get("target") or "party"),
                    text=text,
                    metadata={
                        key: payload[key]
                        for key in ("handoff_lead_to", "handoff_reason", "leadership_intent")
                        if key in payload
                    },
                )
            )
        elif action_type == "guard":
            effects.append(Guard(actor_id=hero.id))
        elif action_type == "end_turn":
            effects.append(EndTurn(actor_id=hero.id))
        elif action_type == "call_extraction":
            effects.append(CallExtraction(actor_id=hero.id))
        return effects


class EngineRuntime:
    """Owns action validation, effect queues, triggers, reward, and phases."""

    def __init__(self, rules: Any) -> None:
        self.rules = rules
        self.grid = rules.grid
        self.rng = rules.rng
        self.triggers = TriggerRegistry()
        self.resolver = EffectResolver(self)
        self.phase = PhaseController(self)
        self.translator = ActionTranslator(self)
        self.state_for_effects: GameState | None = None
        self._registered_quests: set[str] = set()
        self._registered_mechanics: set[str] = set()

    def apply_action(
        self, state: GameState, agent_id: str, action: dict[str, Any]
    ) -> tuple[float, str, dict[str, Any]]:
        self.state_for_effects = state
        self._register_mechanics_once(state)
        self._register_hooks_once(state.quest_id)
        if state.done:
            return 0.0, "The quest is already over.", {"done": True}
        failure = self.validate(state, agent_id, action)
        if failure:
            state.invalid_actions += 1
            if action.get("type") == "message" and failure.reason in {
                "communication_disabled",
                "not_designated_leader",
                "unknown_recipient",
                "unknown_sender",
            }:
                protocol_from_state(state).submit(state, agent_id, action)
            feedback = self.rules._invalid_feedback(
                state, agent_id, action, failure.reason, failure.message
            )
            state.trace.append(
                {
                    "kind": "validation_failed",
                    "round": state.round,
                    "agent_id": agent_id,
                    "reason": failure.reason,
                    "action": dict(action),
                }
            )
            return (
                0.0,
                f"Invalid action for {agent_id}: {failure.message}",
                {"invalid": True, **feedback},
            )

        known_before = set(state.known_tiles)
        room_ids_before = self.rules._known_room_ids(state, known_before)
        ctx = ResolverContext(state=state, runtime=self, actor_id=agent_id, action=action)
        ctx.add_reward(-0.01)
        emitted_effects = self.translator.translate(state, agent_id, action)
        state.trace.append(
            {
                "kind": "action_pipeline",
                "round": state.round,
                "agent_id": agent_id,
                "action": dict(action),
                "emitted_effects": [
                    self.resolver._effect_record(effect) for effect in emitted_effects
                ],
            }
        )
        self.resolver.resolve_many(ctx, emitted_effects)
        self._apply_flag_deltas(state, ctx)
        self.grid.update_known_tiles(state)
        awareness_events = self.grid.update_monster_awareness(
            state, reason=str(action.get("type", "action"))
        )
        if awareness_events:
            ctx.info["awareness_events"] = awareness_events
        scout_reward, scout_info = self.rules._scout_reward(
            state, known_before=known_before, room_ids_before=room_ids_before
        )
        if scout_reward:
            ctx.add_reward(scout_reward)
            state.scout_reward += scout_reward
            ctx.emit_text(
                f"Scout progress: +{scout_info['new_floor_tiles']} floor tiles, +{scout_info['new_rooms']} rooms."
            )
        else:
            scout_info = scout_info or {}
        self.phase.check_end_conditions(state)
        if state.done and state.winner == "heroes":
            ctx.add_reward(1.0)
            ctx.emit_text("The heroes complete the objective and escape.")
        elif state.done and state.winner == "dungeon":
            ctx.add_reward(-1.0)
            ctx.emit_text("The dungeon prevails.")
        self.phase.finish_action(state, agent_id, str(action.get("type")))
        narration = " ".join(text for text in ctx.texts if text).strip() or "Nothing happens."
        info = {"scout_reward": round(scout_reward, 4), **scout_info, **ctx.info}
        if ctx.resolved_effects:
            info["resolved_effects"] = ctx.resolved_effects
        if ctx.triggered_reactions:
            info["triggered_reactions"] = ctx.triggered_reactions
        furniture_result = state.scripts.pop("_last_furniture_result", None)
        if furniture_result:
            info["furniture_result"] = furniture_result
        return ctx.reward, narration, info

    def _register_hooks_once(self, quest_id: str) -> None:
        if quest_id in self._registered_quests:
            return
        hooks = getattr(self.rules, "hooks", None)
        register = getattr(hooks, "register", None)
        if callable(register):
            register(quest_id, self.triggers)
        self._registered_quests.add(quest_id)

    def _register_mechanics_once(self, state: GameState) -> None:
        quest_id = state.quest_id
        if quest_id in self._registered_mechanics:
            return
        mechanics = state.scripts.get("mechanics")
        if not isinstance(mechanics, dict):
            self._registered_mechanics.add(quest_id)
            return
        for event_name, spec in mechanics.items():
            rules = spec if isinstance(spec, list) else [spec]
            self.triggers.on(str(event_name), self._mechanic_handler(str(event_name), rules))
        self._registered_mechanics.add(quest_id)

    def _mechanic_handler(
        self, event_name: str, rules: list[Any]
    ) -> Callable[[ResolverContext], Iterable[Effect] | None]:
        def handler(ctx: ResolverContext) -> list[Effect]:
            effects: list[Effect] = []
            for rule in rules:
                if not isinstance(rule, dict):
                    effects.extend(self.resolver.raw_effects(ctx.actor_id, event_name, rule))
                    continue
                if not self._mechanic_condition_matches(ctx, rule.get("if")):
                    continue
                payloads = rule.get("then", rule.get("effects", rule))
                effects.extend(self._mechanic_effects(ctx, event_name, payloads))
            return effects

        return handler

    def _mechanic_condition_matches(self, ctx: ResolverContext, condition: Any) -> bool:
        if not condition:
            return True
        if isinstance(condition, list):
            return all(self._mechanic_condition_matches(ctx, item) for item in condition)
        if not isinstance(condition, dict):
            return bool(condition)
        state = ctx.state
        payload = (
            ctx.info.get("trigger_payload")
            if isinstance(ctx.info.get("trigger_payload"), dict)
            else {}
        )
        if "flag" in condition and not state.scripts.get(str(condition["flag"])):
            return False
        if "not_flag" in condition and state.scripts.get(str(condition["not_flag"])):
            return False
        if "counter_gte" in condition:
            key = str(condition.get("key", ""))
            if int(state.scripts.get(key, 0)) < int(condition["counter_gte"]):
                return False
        if "round_mod" in condition:
            divisor = int(condition.get("round_mod", 1))
            equals = int(condition.get("equals", 0))
            if divisor and state.round % divisor != equals:
                return False
        if "objective_carrier" in condition and bool(state.objective.carrier) != bool(
            condition["objective_carrier"]
        ):
            return False
        if "action_type" in condition and str(ctx.action.get("type")) != str(
            condition["action_type"]
        ):
            return False
        if "target" in condition and str(ctx.action.get("target")) != str(condition["target"]):
            return False
        if "payload_key" in condition:
            key = str(condition["payload_key"])
            if payload.get(key) != condition.get("payload_value", payload.get(key)):
                return False
        return True

    def _mechanic_effects(
        self, ctx: ResolverContext, source_id: str, payloads: Any
    ) -> list[Effect]:
        effects: list[Effect] = []
        raw_list = payloads if isinstance(payloads, list) else [payloads]
        for raw in raw_list:
            if not isinstance(raw, dict):
                effects.extend(self.resolver.raw_effects(ctx.actor_id, source_id, raw))
                continue
            kind = str(raw.get("type", "emit"))
            if kind in {"set_flag", "set_script"}:
                effects.append(SetFlag(key=str(raw.get("key", "")), value=raw.get("value", True)))
            elif kind == "increment_counter":
                effects.append(
                    IncrementCounter(
                        key=str(raw.get("key", "")),
                        amount=int(raw.get("amount", 1)),
                        default=int(raw.get("default", 0)),
                    )
                )
            elif kind in {"alert", "modify_alert"}:
                effects.append(ModifyAlert(amount=int(raw.get("amount", raw.get("alert", 0)))))
            elif kind in {"spawn_monster", "spawn_monster_once"}:
                pos = raw.get("pos")
                effects.append(
                    SpawnMonster(
                        monster_id=str(raw.get("id", "")),
                        role=str(raw.get("role", "skitterling")),
                        pos=tuple(pos) if isinstance(pos, list) and len(pos) == 2 else None,
                        activation=str(raw.get("activation", "engaged")),
                        status=[str(item) for item in raw.get("status", [])]
                        if isinstance(raw.get("status"), list)
                        else [],
                    )
                )
            elif kind == "spawn_monster_near":
                fallback = raw.get("fallback_pos") or raw.get("pos")
                effects.append(
                    SpawnMonsterNear(
                        monster_id=str(raw.get("id", "")),
                        role=str(raw.get("role", "skitterling")),
                        anchor_id=str(raw.get("anchor_id", ctx.actor_id)),
                        fallback_pos=tuple(fallback)
                        if isinstance(fallback, list) and len(fallback) == 2
                        else None,
                        activation=str(raw.get("activation", "engaged")),
                        status=[str(item) for item in raw.get("status", [])]
                        if isinstance(raw.get("status"), list)
                        else [],
                    )
                )
            elif kind == "unlock_achievement":
                effects.append(
                    UnlockAchievement(
                        achievement_id=str(raw.get("id", raw.get("achievement_id", ""))),
                        title=str(raw.get("title", "")),
                        reward=float(raw.get("reward", 0.0)),
                        layer=str(raw.get("layer", "quest")),
                        description=str(raw.get("description", "")),
                    )
                )
            else:
                effects.extend(self.resolver.raw_effects(ctx.actor_id, source_id, raw))
        return effects

    def emit_trigger(
        self, ctx: ResolverContext, name: str, payload: dict[str, Any] | None = None
    ) -> list[Effect]:
        handlers = self.triggers.handlers(name)
        if not handlers:
            return []
        old_payload = ctx.info.get("trigger_payload")
        trigger_payload = dict(payload or {})
        ctx.info["trigger_payload"] = trigger_payload
        try:
            effects = self.triggers.emit(name, ctx)
        finally:
            if old_payload is None:
                ctx.info.pop("trigger_payload", None)
            else:
                ctx.info["trigger_payload"] = old_payload
        ctx.state.trace.append(
            {
                "kind": "typed_trigger",
                "round": ctx.state.round,
                "trigger_name": name,
                "agent_id": ctx.actor_id,
                "payload": trigger_payload,
                "handler_count": len(handlers),
                "emitted_effects": [self.resolver._effect_record(effect) for effect in effects],
            }
        )
        return effects

    def validate(
        self, state: GameState, agent_id: str, action: dict[str, Any]
    ) -> ValidationFailure | None:
        active = state.active_agent()
        if agent_id != active:
            return ValidationFailure(
                "not_active_agent",
                f"{agent_id} is not active; {active} must act.",
                action,
                agent_id,
            )
        if action.get("type") == "message":
            result = protocol_from_state(state).submit_preview(state, agent_id, action)
            if not result.accepted:
                return ValidationFailure(result.reason, result.message, action, agent_id)
        legal = self.rules.legal_actions(state, agent_id)
        if not self.rules._action_is_legal(action, legal):
            reason, message = self.rules._classify_illegal_action(state, agent_id, action, legal)
            return ValidationFailure(reason, message, action, agent_id)
        return None

    def classic_enabled(self, state: GameState) -> bool:
        return bool(state.ruleset)

    def ruleset_enabled(self, state: GameState, key: str) -> bool:
        return bool((state.ruleset.get(key) or {}).get("enabled"))

    def is_major_action(self, state: GameState, action_type: str) -> bool:
        if action_type not in MAJOR_ACTION_TYPES:
            return False
        if action_type == "open_door":
            return bool(state.ruleset.get("one_major_action", {}).get("open_door_is_major", True))
        return True

    def increment_social_metric(
        self, state: GameState, metric: str, hero_id: str | None = None, amount: int = 1
    ) -> None:
        if hero_id:
            current = state.social_metrics.get(metric)
            if isinstance(current, dict):
                current[hero_id] = int(current.get(hero_id, 0)) + amount
                return
        state.social_metrics[metric] = int(state.social_metrics.get(metric, 0)) + amount

    def deterministic_warden_dread_effects(self, state: GameState) -> list[Effect]:
        if not self.ruleset_enabled(state, "warden_dread") or state.dread <= 0:
            return []
        carrier = state.objective.carrier
        if carrier and carrier in state.heroes:
            return [WardenSpendDread(effect="pressure_carrier", target_id=carrier, cost=1)]
        recent_bad_draw = any(
            record.get("kind") == "card_draw"
            and record.get("card_type") in {"trap", "wandering_monster", "event"}
            for record in state.trace[-8:]
        )
        if recent_bad_draw:
            target = self._lowest_hp_living_hero(state)
            return (
                [WardenSpendDread(effect="spawn_wanderer", target_id=target.id, cost=1)]
                if target
                else []
            )
        if state.dread >= 1 and state.torch > 4:
            return [WardenSpendDread(effect="darken_lantern", target_id="", cost=1)]
        return []

    def _lowest_hp_living_hero(self, state: GameState) -> Entity | None:
        living = [
            hero
            for hero in state.heroes.values()
            if hero.alive and hero.id not in state.extracted_heroes
        ]
        return min(living, key=lambda hero: hero.hp) if living else None

    def _apply_flag_deltas(self, state: GameState, ctx: ResolverContext) -> None:
        if "_alert_delta" in state.scripts:
            delta = int(state.scripts.pop("_alert_delta"))
            old_alert = state.alert
            state.alert = max(0, state.alert + delta)
            if old_alert != state.alert:
                ctx.emit_text(f"Alert changes from {old_alert} to {state.alert}.")
        if "_treasure_delta" in state.scripts:
            amount = int(state.scripts.pop("_treasure_delta"))
            state.treasure_collected += amount
            if ctx.actor_id in state.heroes:
                state.hero_treasure[ctx.actor_id] = (
                    state.hero_treasure.get(ctx.actor_id, 0) + amount
                )
                stats = state.per_hero_stats.setdefault(
                    ctx.actor_id, default_per_hero_stats(state.heroes[ctx.actor_id])
                )
                stats["treasure"] = int(stats.get("treasure", 0)) + amount
            ctx.add_reward(0.1)
        grants = [key for key in state.scripts if key.startswith("_grant_spell:")]
        for key in grants:
            _, hero_id, spell = key.split(":", 2)
            hero = state.heroes.get(hero_id)
            if hero:
                hero.equipment.setdefault("spell_cards", []).append(spell)
                ctx.emit_text(
                    f"{hero.role} learns {SPELL_CARDS.get(spell, {}).get('name', spell)}."
                )
                ctx.add_reward(0.1)
            state.scripts.pop(key, None)

    def roll_successes(self, dice: int) -> int:
        return sum(1 for _ in range(max(0, dice)) if self.rng.randint(1, 6) >= 5)

    def equipped_weapon(self, hero: Entity) -> dict[str, Any] | None:
        item_id = hero.equipment.get("weapon")
        return WEAPON_ITEMS.get(str(item_id)) if item_id else None

    def weapon_range(self, hero: Entity) -> int:
        weapon = self.equipped_weapon(hero)
        if not weapon:
            return 5 if hero.role == "wizard" else 1
        if "ranged_dice" in weapon:
            return int(weapon.get("range", 1))
        return 5 if hero.role == "wizard" else int(weapon.get("range", 1))

    def attack_dice(self, attacker: Entity, *, ranged: bool) -> int:
        weapon = self.equipped_weapon(attacker)
        if ranged:
            if weapon and "ranged_dice" in weapon:
                return max(1, int(weapon["ranged_dice"]))
            if attacker.role == "wizard":
                focus_bonus = int(weapon.get("focus_bonus", 0)) if weapon else 0
                return max(2, (attacker.focus + focus_bonus) // 2)
            return max(1, attacker.attack - 1)
        if weapon and "melee_dice" in weapon:
            return max(1, int(weapon["melee_dice"]))
        if attacker.team == "dungeon":
            return max(
                1,
                attacker.attack
                + int(attacker.equipment.get("phase_attack_bonus", 0))
                - (1 if "weakened" in attacker.status else 0),
            )
        return max(1, attacker.attack)

    def hero_guard(self, hero: Entity, *, ranged: bool = False) -> int:
        if hero.team != "heroes":
            return hero.guard
        guard = hero.guard
        for slot, item_id in hero.equipment.items():
            if slot == "weapon":
                continue
            item = ARMOR_ITEMS.get(str(item_id))
            if not item:
                continue
            guard += int(item.get("guard", 0))
            if ranged:
                guard += int(item.get("ranged_guard", 0))
        return max(0, guard)

    def item_name(self, item_id: str) -> str:
        return str(
            (
                WEAPON_ITEMS.get(item_id)
                or ARMOR_ITEMS.get(item_id)
                or SPELL_CARDS.get(item_id)
                or {}
            ).get("name", item_id)
        )

    def is_equippable(self, item_id: str) -> bool:
        return item_id in WEAPON_ITEMS or item_id in ARMOR_ITEMS

    def item_slot(self, item_id: str) -> str:
        if item_id in WEAPON_ITEMS:
            return "weapon"
        return str(ARMOR_ITEMS.get(item_id, {}).get("slot", "item"))

    def refresh_equipment_stats(self, hero: Entity) -> None:
        base = HERO_ARCHETYPES.get(hero.role, {})
        hero.speed = max(
            1,
            int(base.get("speed", hero.speed))
            + sum(
                int(ARMOR_ITEMS.get(str(item_id), {}).get("speed", 0))
                for slot, item_id in hero.equipment.items()
                if slot != "weapon"
            ),
        )

    def deck_policy(self, state: GameState, deck_id: str) -> dict[str, Any]:
        policies = state.scripts.get("deck_policies", {})
        if deck_id == "treasure" and self.ruleset_enabled(state, "treasure_risk"):
            policy = (
                dict(policies.get(deck_id, {}))
                if isinstance(policies, dict) and isinstance(policies.get(deck_id), dict)
                else {}
            )
            policy["reshuffle"] = True
            policy.setdefault("identity", "push_your_luck")
            return policy
        if isinstance(policies, dict) and isinstance(policies.get(deck_id), dict):
            return dict(policies[deck_id])
        if deck_id == "event":
            return {"reshuffle": True}
        return {"reshuffle": False}

    def effect_target_monsters(
        self, state: GameState | None, payload: dict[str, Any]
    ) -> list[Entity]:
        if state is None:
            return []
        if payload.get("target"):
            monster = state.monsters.get(str(payload["target"]))
            return [monster] if monster else []
        role = payload.get("role")
        if role:
            return [
                monster
                for monster in state.monsters.values()
                if monster.alive and monster.role == role
            ]
        if payload.get("nearest_to_objective"):
            targets = [monster for monster in state.monsters.values() if monster.alive]
            if state.objective.pos:
                targets.sort(
                    key=lambda monster: self.grid.manhattan(monster.pos, state.objective.pos)
                )
            return targets[:1]
        return []

    def nearest_free_adjacent(self, state: GameState, pos: Pos) -> Pos | None:
        for candidate in self.grid.adjacent_positions(pos):
            if self.grid.is_walkable(state, candidate):
                return candidate
        return None

    def pos_from_target(self, target: Any, default: Pos) -> Pos:
        if isinstance(target, (list, tuple)) and len(target) == 2:
            return int(target[0]), int(target[1])
        return default

    def run_script(self, state: GameState, script_name: str) -> None:
        script = state.scripts.get(script_name)
        if not isinstance(script, dict):
            return
        ctx = ResolverContext(
            state=state, runtime=self, actor_id=state.active_agent(), action={"type": script_name}
        )
        effects: list[Effect] = []
        if script.get("message"):
            effects.append(EmitEvent(message=str(script["message"])))
        for raw in script.get("effects", []):
            effects.extend(self.resolver.raw_effects(ctx.actor_id, script_name, raw))
        self.resolver.resolve_many(ctx, effects)
