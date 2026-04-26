"""RulesEngine: legal actions, action resolution, combat, turn order, reward."""

from __future__ import annotations

import random
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
)
from .grid_engine import GridEngine


class RulesEngine:
    """Resolves DungeonGrid actions against a GameState."""

    def __init__(self, grid: GridEngine, rng: random.Random | None = None) -> None:
        self.grid = grid
        self.rng = rng or random.Random()
        self._runtime = None

    def legal_actions(self, state: GameState, agent_id: str) -> list[dict[str, Any]]:
        if state.done or state.phase == "done":
            return []
        active = state.active_agent()
        if agent_id != active:
            return []
        if agent_id == "warden":
            return self._warden_legal_actions(state)
        hero = state.heroes.get(agent_id)
        if hero is None or not hero.alive:
            return [{"type": "end_turn"}]
        actions: list[dict[str, Any]] = []
        ap = state.ap_remaining.get(agent_id, 0)
        classic = self._classic_enabled(state)
        movement = state.movement_remaining.get(agent_id, 0)
        major_available = not classic or not state.major_action_used.get(agent_id, False)
        visible = self.grid.visible_tiles(state, agent_id)
        if ap >= 1:
            actions.append({"type": "message", "target": "party"})
            for ally_id in state.heroes:
                if ally_id != agent_id:
                    actions.append({"type": "message", "target": ally_id})
            if not classic or movement > 0:
                for direction, (dx, dy) in DIRECTIONS.items():
                    target = (hero.pos[0] + dx, hero.pos[1] + dy)
                    if self.grid.is_walkable(state, target):
                        actions.append(
                            {"type": "move", "direction": direction, "target": list(target)}
                        )
            if major_available:
                for door in state.doors.values():
                    if (
                        door.state == "closed"
                        and door.pos in self.grid.adjacent_positions(hero.pos)
                        and (not door.secret or door.discovered)
                    ):
                        actions.append({"type": "open_door", "target": door.id})
            for pos in [hero.pos, *self.grid.adjacent_positions(hero.pos)]:
                if self.grid.in_bounds(state, pos):
                    actions.append({"type": "inspect_tile", "target": list(pos)})
            safe_search = not classic or not self._safe_room_search_blocked(state, hero)
            if major_available:
                for chest in state.chests.values():
                    if (
                        not chest.opened
                        and self.grid.manhattan(hero.pos, chest.pos) <= 1
                        and chest.pos in visible
                    ):
                        actions.append({"type": "interact", "target": chest.id})
                        if safe_search:
                            actions.append({"type": "search_treasure", "target": chest.id})
                for furniture in state.furniture.values():
                    if (
                        furniture.visible
                        and not furniture.destroyed
                        and self.grid.manhattan(hero.pos, furniture.pos) <= 1
                        and furniture.pos in visible
                    ):
                        if "interact" not in furniture.searched_categories:
                            actions.append({"type": "interact", "target": furniture.id})
                        if safe_search and "treasure" not in furniture.searched_categories:
                            actions.append({"type": "search_treasure", "target": furniture.id})
                        if safe_search and "furniture" not in furniture.searched_categories:
                            actions.append({"type": "search_furniture", "target": furniture.id})
            if (
                major_available
                and state.objective.pos
                and self.grid.manhattan(hero.pos, state.objective.pos) <= 1
                and state.objective.pos in visible
            ):
                actions.append({"type": "interact", "target": state.objective.id})
            if hero.pos == state.escape_tile and (
                state.objective.carrier == hero.id or (classic and state.objective.recovered)
            ):
                actions.append({"type": "interact", "target": "escape"})
            if (
                classic
                and state.objective.recovered
                and state.ruleset.get("extraction", {}).get("allow_partial", True)
            ):
                actions.append({"type": "call_extraction"})
            for item in hero.inventory:
                if item in {"healing_draught", "lantern_lens"}:
                    actions.append({"type": "use_item", "target": item})
                if (
                    self._is_equippable(item)
                    and self._can_equip(hero, item)
                    and hero.equipment.get(self._item_slot(item)) != item
                ):
                    actions.append({"type": "equip_item", "target": item})
            for ally_id, ally in state.heroes.items():
                if (
                    ally_id != hero.id
                    and ally.alive
                    and self.grid.manhattan(hero.pos, ally.pos) <= 1
                ):
                    for item in hero.inventory:
                        if item != state.objective.id:
                            actions.append(
                                {"type": "give_item", "target": ally_id, "payload": {"item": item}}
                            )
            actions.append({"type": "guard"})
        if ap >= 2 and major_available:
            for monster in state.monsters.values():
                if monster.alive and monster.pos in visible:
                    if self.grid.manhattan(hero.pos, monster.pos) == 1:
                        actions.append({"type": "attack_melee", "target": monster.id})
                    weapon_range = self._weapon_range(hero)
                    if (
                        weapon_range > 1
                        and self.grid.manhattan(hero.pos, monster.pos) <= weapon_range
                        and self.grid.line_clear(state, hero.pos, monster.pos)
                    ):
                        actions.append({"type": "attack_ranged", "target": monster.id})
                    if (
                        self._can_cast_spell(hero, "spark_lance")
                        and self.grid.manhattan(hero.pos, monster.pos)
                        <= int(SPELL_CARDS["spark_lance"].get("range", 5))
                        and self.grid.line_clear(state, hero.pos, monster.pos)
                    ):
                        actions.append(
                            {
                                "type": "cast",
                                "target": monster.id,
                                "payload": {"spell": "spark_lance"},
                            }
                        )
            if hero.role == "elf":
                for ally in state.heroes.values():
                    if (
                        self._can_cast_spell(hero, "mend_wounds")
                        and ally.alive
                        and ally.hp < ally.max_hp
                        and self.grid.manhattan(hero.pos, ally.pos) <= 1
                    ):
                        actions.append(
                            {"type": "cast", "target": ally.id, "payload": {"spell": "mend_wounds"}}
                        )
            for ally in state.heroes.values():
                if ally.alive and self.grid.manhattan(hero.pos, ally.pos) <= 1:
                    if self._can_cast_spell(hero, "ward_circle"):
                        actions.append(
                            {"type": "cast", "target": ally.id, "payload": {"spell": "ward_circle"}}
                        )
                    if self._can_cast_spell(hero, "quiet_step"):
                        actions.append(
                            {"type": "cast", "target": ally.id, "payload": {"spell": "quiet_step"}}
                        )
            if self._can_cast_spell(hero, "blink_step"):
                for direction, (dx, dy) in DIRECTIONS.items():
                    first = (hero.pos[0] + dx, hero.pos[1] + dy)
                    second = (hero.pos[0] + 2 * dx, hero.pos[1] + 2 * dy)
                    if self.grid.is_walkable(state, first) or self.grid.is_walkable(state, second):
                        actions.append(
                            {
                                "type": "cast",
                                "target": direction,
                                "payload": {"spell": "blink_step"},
                            }
                        )
            for spell in ("reveal_glyph", "hush_flame", "silence"):
                if self._can_cast_spell(hero, spell):
                    actions.append({"type": "cast", "target": hero.id, "payload": {"spell": spell}})
            for trap in state.traps.values():
                if (
                    trap.armed
                    and trap.revealed
                    and self.grid.manhattan(hero.pos, trap.pos) <= 1
                    and not self._specialist_action_blocked(state, hero, "disarm")
                ):
                    actions.append({"type": "disarm", "target": trap.id})
            for furniture in state.furniture.values():
                if (
                    furniture.visible
                    and furniture.destructible
                    and not furniture.destroyed
                    and self.grid.manhattan(hero.pos, furniture.pos) <= 1
                    and furniture.pos in visible
                ):
                    actions.append({"type": "attack_object", "target": furniture.id})
            if not classic or not self._safe_room_search_blocked(state, hero):
                actions.append({"type": "inspect_room"})
                actions.append({"type": "search_traps"})
                actions.append({"type": "search_secrets"})
        actions.append({"type": "end_turn"})
        return self._dedupe_actions(actions)

    def _warden_legal_actions(self, state: GameState) -> list[dict[str, Any]]:
        actions = [{"type": "warden_auto"}]
        if state.ruleset.get("warden_dread", {}).get("enabled") and state.dread > 0:
            for hero in state.heroes.values():
                if hero.alive and hero.id not in state.extracted_heroes:
                    actions.append(
                        {
                            "type": "warden_spend_dread",
                            "target": hero.id,
                            "payload": {"effect": "spawn_wanderer"},
                        }
                    )
                    actions.append(
                        {
                            "type": "warden_spend_dread",
                            "target": hero.id,
                            "payload": {"effect": "pressure_carrier"},
                        }
                    )
            actions.append(
                {
                    "type": "warden_spend_dread",
                    "target": "torch",
                    "payload": {"effect": "darken_lantern"},
                }
            )
        for monster in state.monsters.values():
            if monster.alive and monster.activation != "dormant":
                actions.append({"type": "activate_monster", "target": monster.id})
        actions.append({"type": "end_turn"})
        return actions

    def _classic_enabled(self, state: GameState) -> bool:
        return bool(state.ruleset)

    def _required_roles(self, state: GameState) -> list[str]:
        requirements = state.scripts.get("role_requirements", {})
        if not isinstance(requirements, dict):
            return []
        return [str(role) for role in requirements.get("required_roles", [])]

    def _specialist_action_blocked(self, state: GameState, hero: Entity, action_type: str) -> bool:
        if not self._classic_enabled(state) or action_type != "disarm":
            return False
        required = self._required_roles(state)
        return bool(required and hero.role not in required)

    def _is_major_action(self, state: GameState, action_type: str) -> bool:
        if action_type not in MAJOR_ACTION_TYPES:
            return False
        if action_type == "open_door":
            return bool(state.ruleset.get("one_major_action", {}).get("open_door_is_major", True))
        return True

    def _safe_room_search_blocked(self, state: GameState, hero: Entity) -> bool:
        spec = state.ruleset.get("safe_room_search", {})
        if not spec.get("enabled"):
            return False
        visible = self.grid.visible_tiles(state, hero.id)
        hero_room = self.grid.room_id_at(state.rooms, hero.pos)
        for monster in state.monsters.values():
            if not monster.alive:
                continue
            if monster.activation == "dormant" and not spec.get("include_dormant_monsters", False):
                continue
            if hero_room and monster.room_id == hero_room:
                return True
            if (
                spec.get("include_visible_corridor_monsters", True)
                and monster.pos in visible
                and monster.activation != "dormant"
            ):
                return True
        return False

    def _dedupe_actions(self, actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        result: list[dict[str, Any]] = []
        for action in actions:
            key = repr(sorted(action.items()))
            if key not in seen:
                seen.add(key)
                result.append(action)
        return result

    def apply_action(
        self, state: GameState, agent_id: str, action: dict[str, Any]
    ) -> tuple[float, str, dict[str, Any]]:
        """Apply an action. Returns reward, narration, info."""
        return self._runtime_for_step().apply_action(state, agent_id, action)

    def _runtime_for_step(self):
        """Return the action runtime, keeping RNG synchronized with this rules engine."""
        if self._runtime is None:
            from .engine_runtime import EngineRuntime

            self._runtime = EngineRuntime(self)
        self._runtime.rng = self.rng
        return self._runtime

    def _invalid_feedback(
        self,
        state: GameState,
        agent_id: str,
        action: dict[str, Any],
        reason: str,
        message: str,
    ) -> dict[str, Any]:
        hero = state.heroes.get(agent_id)
        feedback = {
            "round": state.round,
            "agent_id": agent_id,
            "action": dict(action),
            "reason": reason,
            "message": message,
            "position": list(hero.pos) if hero else None,
            "ap_remaining": state.ap_remaining.get(agent_id),
        }
        state.invalid_feedback.append(feedback)
        return {"invalid_reason": reason, "invalid_feedback": feedback}

    def _classify_illegal_action(
        self,
        state: GameState,
        agent_id: str,
        action: dict[str, Any],
        legal: list[dict[str, Any]],
    ) -> tuple[str, str]:
        action_type = action.get("type")
        if not action_type:
            return "unknown_action_type", "Action is missing a type."
        known_types = set(ACTION_COSTS)
        if action_type not in known_types:
            return "unknown_action_type", f"{action_type} is not a known action type."
        hero = state.heroes.get(agent_id)
        if hero and self._classic_enabled(state):
            if self._specialist_action_blocked(state, hero, str(action_type)):
                required = ", ".join(self._required_roles(state))
                return (
                    "wrong_role",
                    f"{action_type} is a specialist action here; required role: {required}.",
                )
            if action_type == "move" and state.movement_remaining.get(agent_id, 0) <= 0:
                return "insufficient_movement", f"{agent_id} has no movement remaining this turn."
            if self._is_major_action(state, str(action_type)) and state.major_action_used.get(
                agent_id, False
            ):
                return (
                    "major_action_already_used",
                    f"{agent_id} already used a major action this turn.",
                )
            blocked_search_actions = set(
                state.ruleset.get("safe_room_search", {}).get("block_search_actions", [])
            )
            if action_type in blocked_search_actions and self._safe_room_search_blocked(
                state, hero
            ):
                return (
                    "unsafe_search",
                    "Search actions are blocked while monsters threaten the area.",
                )
        effective_cost = (
            0
            if hero and self._classic_enabled(state) and action_type == "move"
            else ACTION_COSTS.get(str(action_type), 0)
        )
        if hero and state.ap_remaining.get(agent_id, 0) < effective_cost:
            return (
                "insufficient_ap",
                f"{action_type} requires more AP than {agent_id} has remaining.",
            )
        if action_type == "move":
            direction = action.get("direction")
            if direction not in DIRECTIONS:
                return "missing_target", "Move requires a cardinal direction."
            dx, dy = DIRECTIONS[direction]
            target = (hero.pos[0] + dx, hero.pos[1] + dy) if hero else (0, 0)
            if not self.grid.is_walkable(state, target):
                return "blocked_movement", f"Cannot move {direction}; the target tile is blocked."
        if (
            action_type
            in {
                "open_door",
                "attack_melee",
                "attack_ranged",
                "cast",
                "disarm",
                "interact",
                "search_treasure",
                "search_furniture",
                "attack_object",
                "give_item",
                "warden_spend_dread",
            }
            and action.get("target") is None
        ):
            return "missing_target", f"{action_type} requires a target."
        if hero and action_type in {"interact", "open_door", "search_treasure", "search_furniture", "disarm"}:
            guidance = self._proximity_guidance(state, hero, str(action_type), action.get("target"))
            if guidance:
                return guidance
        matching_type = [candidate for candidate in legal if candidate.get("type") == action_type]
        if matching_type:
            return "illegal_target", f"{action_type} target or fields are not currently legal."
        return "illegal_action", f"{action_type} is not currently legal."

    def _proximity_guidance(
        self,
        state: GameState,
        hero: Entity,
        action_type: str,
        target: Any,
    ) -> tuple[str, str] | None:
        target_id = str(target)
        target_pos = None
        visible_tiles = self.grid.visible_tiles(state, hero.id)
        if action_type == "open_door" and target_id in state.doors:
            door = state.doors[target_id]
            if door.pos not in visible_tiles or (door.secret and not door.discovered):
                return None
            target_pos = door.pos
        elif action_type in {"search_treasure", "search_furniture"}:
            if target_id in state.chests:
                chest = state.chests[target_id]
                if chest.pos not in visible_tiles:
                    return None
                target_pos = chest.pos
            elif target_id in state.furniture:
                furniture = state.furniture[target_id]
                if not furniture.visible or furniture.pos not in visible_tiles:
                    return None
                target_pos = furniture.pos
        elif action_type == "disarm" and target_id in state.traps:
            trap = state.traps[target_id]
            if not trap.revealed or trap.pos not in visible_tiles:
                return None
            target_pos = trap.pos
        elif action_type == "interact":
            if target_id == state.objective.id and state.objective.pos is not None:
                if state.objective.pos not in visible_tiles:
                    return None
                target_pos = state.objective.pos
            elif target_id in state.chests:
                chest = state.chests[target_id]
                if chest.pos not in visible_tiles:
                    return None
                target_pos = chest.pos
            elif target_id in state.furniture:
                furniture = state.furniture[target_id]
                if not furniture.visible or furniture.pos not in visible_tiles:
                    return None
                target_pos = furniture.pos
            elif target_id == "escape":
                if hero.pos != state.escape_tile:
                    return (
                        "not_at_escape",
                        f"{hero.id} must stand on escape tile {list(state.escape_tile)} before interacting with escape.",
                    )
                if state.objective.carrier != hero.id and not state.objective.recovered:
                    return (
                        "objective_not_carried",
                        f"{hero.id} must carry {state.objective.id} before escaping with the objective.",
                    )
        if target_pos is None:
            return None
        distance = self.grid.manhattan(hero.pos, target_pos)
        if distance > 1:
            return (
                "not_adjacent",
                f"{action_type} target {target_id} is visible/referenced but not adjacent "
                f"(distance {distance}); move to a neighboring open tile before using {action_type}.",
            )
        return None

    def _action_is_legal(self, action: dict[str, Any], legal: list[dict[str, Any]]) -> bool:
        atype = action.get("type")
        for candidate in legal:
            if candidate.get("type") != atype:
                continue
            if "direction" in candidate and action.get("direction") != candidate.get("direction"):
                continue
            if atype == "move" and action.get("target") is None:
                return True
            if "target" in candidate and action.get("target") != candidate.get("target"):
                # Target coordinates may arrive as tuple/list.
                cand_target = candidate.get("target")
                act_target = action.get("target")
                if not (isinstance(cand_target, list) and list(act_target or []) == cand_target):
                    continue
            if atype == "give_item":
                candidate_item = (candidate.get("payload") or {}).get("item")
                action_item = (action.get("payload") or {}).get("item")
                if candidate_item != action_item:
                    continue
            return True
        return False

    def _cost(self, state: GameState, entity: Entity, action_type: str) -> None:
        state.ap_remaining[entity.id] = max(
            0, state.ap_remaining.get(entity.id, 0) - ACTION_COSTS.get(action_type, 0)
        )

    def _scout_reward(
        self,
        state: GameState,
        *,
        known_before: set[Pos],
        room_ids_before: set[int],
    ) -> tuple[float, dict[str, Any]]:
        known_after = set(state.known_tiles)
        new_floor_tiles = [
            pos for pos in known_after - known_before if state.terrain[pos[1]][pos[0]] == "."
        ]
        room_ids_after = self._known_room_ids(state, known_after)
        new_rooms = room_ids_after - room_ids_before
        reward = 0.025 * len(new_floor_tiles) + 0.15 * len(new_rooms)
        info = {
            "new_floor_tiles": len(new_floor_tiles),
            "new_rooms": len(new_rooms),
            "known_room_count": len(room_ids_after),
        }
        return reward, info

    def _known_room_ids(self, state: GameState, known_tiles: set[Pos]) -> set[int]:
        room_ids: set[int] = set()
        for index, room in enumerate(self._room_regions(state)):
            if room & known_tiles:
                room_ids.add(index)
        return room_ids

    def _room_regions(self, state: GameState) -> list[set[Pos]]:
        blocked_doors = {door.pos for door in state.doors.values()}
        floor = {
            (x, y)
            for y, row in enumerate(state.terrain)
            for x, cell in enumerate(row)
            if cell == "." and (x, y) not in blocked_doors
        }
        regions: list[set[Pos]] = []
        while floor:
            start = floor.pop()
            region = {start}
            stack = [start]
            while stack:
                pos = stack.pop()
                for nxt in self.grid.adjacent_positions(pos):
                    if nxt not in floor:
                        continue
                    floor.remove(nxt)
                    region.add(nxt)
                    stack.append(nxt)
            regions.append(region)
        return regions

    def _move_hero(
        self, state: GameState, hero: Entity, action: dict[str, Any]
    ) -> tuple[str, float]:
        direction = action.get("direction")
        dx, dy = DIRECTIONS[direction]
        target = (hero.pos[0] + dx, hero.pos[1] + dy)
        hero.pos = target
        self._cost(state, hero, "move")
        reward = 0.0
        text = f"{hero.role} moves {direction}."
        trap = state.trap_at(target)
        if trap and trap.armed:
            trap.revealed = True
            trap.armed = False
            damage = trap.damage
            hero.hp -= damage
            state.total_damage_taken += damage
            text += f" A hidden trap snaps open, dealing {damage} damage."
            if hero.hp <= 0:
                hero.alive = False
                hero.hp = 0
                text += f" {hero.role} is downed."
                if state.objective.carrier == hero.id and state.objective.fragile:
                    state.done = True
                    state.winner = "dungeon"
                    state.phase = "done"
            reward -= 0.2 * damage
        return text, reward

    def _message(self, state: GameState, hero: Entity, action: dict[str, Any]) -> tuple[str, float]:
        target = str(action.get("target") or "party")
        payload = action.get("payload") if isinstance(action.get("payload"), dict) else {}
        text = str(payload.get("text") or payload.get("message") or "").strip()
        text = " ".join(text.split())[:240]
        if not text:
            text = "(no message)"
        message = {
            "message_id": f"msg_{len(state.party_messages) + 1}",
            "round": state.round,
            "from": hero.id,
            "role": hero.role,
            "to": target,
            "text": text,
        }
        state.party_messages.append(message)
        self._cost(state, hero, "message")
        return f"{hero.role} to {target}: {text}", 0.0

    def _open_door(self, state: GameState, hero: Entity, door_id: str) -> tuple[str, float]:
        door = state.doors[door_id]
        door.state = "open"
        if door.secret:
            door.discovered = True
        self._cost(state, hero, "open_door")
        self.grid.update_known_tiles(state)
        self.grid.update_revealed_rooms(state, reason="door_opened", opener_id=hero.id)
        state.alert += 1
        return f"{hero.role} opens {door.id}; the passage beyond is now visible.", 0.02

    def _attack(
        self, state: GameState, attacker: Entity, target_id: str, ranged: bool = False
    ) -> tuple[str, float]:
        target = (
            state.monsters.get(target_id)
            if attacker.team == "heroes"
            else state.heroes.get(target_id)
        )
        if target is None or not target.alive:
            return "The attack finds no living target.", -0.2
        self._cost(state, attacker, "attack_ranged" if ranged else "attack_melee")
        attack_dice = self._attack_dice(attacker, ranged=ranged)
        if "weakened" in attacker.status:
            attack_dice = max(1, attack_dice - 1)
        hits = self._roll_successes(attack_dice)
        guard_dice = self._hero_guard(target) if target.team == "heroes" else target.guard
        guard_dice += 1 if "guarded" in target.status else 0
        blocks = self._roll_successes(guard_dice)
        damage = max(0, hits - blocks)
        weapon = self._equipped_weapon(attacker)
        if damage and weapon:
            damage += int(weapon.get("bonus_damage_on_hit", 0))
        if target.team == "dungeon" and attacker.team == "heroes":
            if "shielded" in target.status:
                damage = max(0, damage - 1)
            if "vulnerable" in target.status and damage > 0:
                damage += 1
        if "guarded" in target.status:
            target.status.remove("guarded")
        special_text = ""
        if target.team == "dungeon" and attacker.team == "heroes":
            damage, special_text = self._monster_incoming_damage_specials(
                state, attacker, target, damage
            )
        if target.team == "heroes":
            damage, prevention_text = self._apply_hero_defense_prevention(
                state, target, damage, source="lethal"
            )
            special_text += prevention_text
        target.hp -= damage
        if target.team == "dungeon" and attacker.team == "heroes":
            special_text += self._apply_boss_phase_after_damage(state, target, attacker)
        if target.team == "heroes":
            state.total_damage_taken += damage
        killed = False
        if target.hp <= 0:
            if target.team == "dungeon" and self._maybe_revive_hollow_knight(
                state, target, attacker
            ):
                special_text += f" {target.role} rises again."
            else:
                target.alive = False
                target.hp = 0
                killed = True
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
        mode = "ranged" if ranged else "melee"
        weapon_name = weapon.get("name") if weapon else None
        with_weapon = f" with {weapon_name}" if weapon_name else ""
        text = f"{attacker.role} makes a {mode} attack{with_weapon} on {target.role}: {hits} hits, {blocks} blocks, {damage} damage."
        text += special_text
        reward = 0.05 * damage
        if killed:
            text += f" {target.role} is defeated."
            reward += 0.15 if target.team == "dungeon" else -0.3
        return text, reward

    def _cast(
        self, state: GameState, caster: Entity, target_id: str, payload: dict[str, Any]
    ) -> tuple[str, float]:
        spell = str(
            payload.get("spell") or ("mend_wounds" if caster.role == "elf" else "spark_lance")
        )
        spec = SPELL_CARDS.get(spell)
        if not spec:
            return f"{caster.role} does not know spell {spell}.", -0.2
        if not self._can_cast_spell(caster, spell):
            return f"{caster.role} has no usable {spell} spell card.", -0.2
        if spell == "mend_wounds":
            target = state.heroes.get(target_id)
            if not target or not target.alive or self.grid.manhattan(caster.pos, target.pos) > 1:
                return "The healing spell has no valid target.", -0.2
            amount = min(2, target.max_hp - target.hp)
            target.hp += amount
            self._cost(state, caster, "cast")
            self._consume_spell_card(state, caster, spell, target_id=target.id)
            return f"{caster.role} mends {target.role}, restoring {amount} hp.", 0.08 * amount
        if spell == "spark_lance":
            target = state.monsters.get(target_id)
            if not target or not target.alive:
                return "The spark lance has no valid target.", -0.2
            if self.grid.manhattan(caster.pos, target.pos) > int(
                spec.get("range", 5)
            ) or not self.grid.line_clear(state, caster.pos, target.pos):
                return "The spark lance has no clear line to its target.", -0.2
            self._cost(state, caster, "cast")
            hits = self._roll_successes(max(2, caster.focus // 2))
            blocks = self._roll_successes(target.guard)
            damage = max(0, hits - blocks)
            damage, special_text = self._monster_incoming_damage_specials(
                state, caster, target, damage
            )
            target.hp -= damage
            special_text += self._apply_boss_phase_after_damage(state, target, caster)
            killed = target.hp <= 0
            if killed:
                if self._maybe_revive_hollow_knight(state, target, caster):
                    killed = False
                    special_text += f" {target.role} rises again."
                else:
                    target.hp = 0
                    target.alive = False
            text = f"{caster.role} casts spark lance at {target.role}: {damage} damage."
            text += special_text
            if killed:
                text += f" {target.role} is defeated."
            self._consume_spell_card(state, caster, spell, target_id=target.id)
            return text, 0.08 * damage + (0.15 if killed else 0.0)
        if spell == "ward_circle":
            target = state.heroes.get(target_id)
            if not target or not target.alive or self.grid.manhattan(caster.pos, target.pos) > 1:
                return "The ward circle has no adjacent living target.", -0.2
            self._cost(state, caster, "cast")
            if "warded" not in target.status:
                target.status.append("warded")
            self._consume_spell_card(state, caster, spell, target_id=target.id)
            return f"{caster.role} casts ward circle around {target.role}.", 0.08
        if spell == "blink_step":
            if target_id not in DIRECTIONS:
                return "Blink step target must be a cardinal direction.", -0.2
            dx, dy = DIRECTIONS[target_id]
            landing = caster.pos
            for distance in (1, 2):
                candidate = (caster.pos[0] + dx * distance, caster.pos[1] + dy * distance)
                if self.grid.is_walkable(state, candidate):
                    landing = candidate
            if landing == caster.pos:
                return f"{caster.role} cannot blink {target_id}; the way is blocked.", -0.2
            self._cost(state, caster, "cast")
            old = caster.pos
            caster.pos = landing
            self.grid.update_known_tiles(state)
            self._consume_spell_card(state, caster, spell, target_id=target_id)
            return f"{caster.role} blinks from {list(old)} to {list(landing)}.", 0.08
        if spell == "reveal_glyph":
            self._cost(state, caster, "cast")
            found = self._reveal_glyphs_near(state, caster)
            self._consume_spell_card(state, caster, spell, target_id=caster.id)
            if found:
                return (
                    f"{caster.role} reveals hidden glyphs: {', '.join(found)}.",
                    0.08 + 0.03 * len(found),
                )
            return f"{caster.role} casts reveal glyph but finds no hidden marks nearby.", 0.02
        if spell == "quiet_step":
            target = state.heroes.get(target_id)
            if not target or not target.alive or self.grid.manhattan(caster.pos, target.pos) > 1:
                return "Quiet step needs an adjacent living hero.", -0.2
            self._cost(state, caster, "cast")
            if "quiet_step" not in target.status:
                target.status.append("quiet_step")
            self._consume_spell_card(state, caster, spell, target_id=target.id)
            return f"{caster.role} wraps {target.role}'s steps in hush.", 0.06
        if spell in {"hush_flame", "silence"}:
            self._cost(state, caster, "cast")
            old_alert = state.alert
            state.alert = max(0, state.alert - (2 if spell == "hush_flame" else 1))
            state.scripts[f"{spell}_active"] = True
            self._consume_spell_card(state, caster, spell, target_id=caster.id)
            return (
                f"{caster.role} casts {spell}; alert falls from {old_alert} to {state.alert}.",
                0.06 + 0.03 * (old_alert - state.alert),
            )
        return f"{caster.role} does not know spell {spell}.", -0.2

    def _can_cast_spell(self, hero: Entity, spell: str) -> bool:
        spec = SPELL_CARDS.get(spell)
        if not spec:
            return False
        roles = set(spec.get("roles") or [])
        if roles and hero.role not in roles:
            return False
        cards = self._available_spell_cards(hero)
        if spell in cards:
            return True
        return bool(spec.get("reusable")) and (
            hero.ability == spell or spell in hero.equipment.get("spell_cards", [])
        )

    def _available_spell_cards(self, hero: Entity) -> list[str]:
        cards = [str(card) for card in hero.equipment.get("spell_cards", [])]
        used_counts: dict[str, int] = {}
        for card in hero.equipment.get("used_spell_cards", []):
            key = str(card)
            used_counts[key] = used_counts.get(key, 0) + 1
        available: list[str] = []
        for card in cards:
            if used_counts.get(card, 0) > 0:
                used_counts[card] -= 1
                continue
            available.append(card)
        return available

    def _consume_spell_card(
        self, state: GameState, hero: Entity, spell: str, *, target_id: str
    ) -> None:
        spec = SPELL_CARDS.get(spell, {})
        if not spec.get("reusable", False):
            used = list(hero.equipment.get("used_spell_cards", []))
            if spell not in used:
                used.append(spell)
            hero.equipment["used_spell_cards"] = used
        event = {
            "kind": "spell_used",
            "round": state.round,
            "agent_id": hero.id,
            "role": hero.role,
            "spell": spell,
            "school": spec.get("school"),
            "target": target_id,
        }
        state.trace.append(event)
        state.event_log.append(f"{hero.role} casts {spell}.")

    def _reveal_glyphs_near(self, state: GameState, caster: Entity) -> list[str]:
        visible = self.grid.visible_tiles(state, caster.id)
        search_area = {caster.pos, *self.grid.adjacent_positions(caster.pos), *visible}
        found: list[str] = []
        for trap in state.traps.values():
            if trap.pos in search_area and trap.armed and not trap.revealed:
                trap.revealed = True
                found.append(trap.id)
        for door in state.doors.values():
            if door.pos in search_area and door.secret and not door.discovered:
                door.discovered = True
                found.append(door.id)
        for furniture in state.furniture.values():
            if furniture.pos in search_area and not furniture.visible:
                furniture.visible = True
                found.append(furniture.id)
        if found:
            state.trace.append(
                {
                    "kind": "spell_reveal",
                    "round": state.round,
                    "agent_id": caster.id,
                    "found": list(found),
                }
            )
        return found

    def _monster_incoming_damage_specials(
        self,
        state: GameState,
        attacker: Entity,
        monster: Entity,
        damage: int,
    ) -> tuple[int, str]:
        if damage <= 0:
            return damage, ""
        if monster.role != "mirror_adept" or "mirror_decoy_spent" in monster.status:
            boss_damage, boss_text = self._boss_incoming_damage_gate(
                state, attacker, monster, damage
            )
            return boss_damage, boss_text
        monster.status.append("mirror_decoy_spent")
        self._record_monster_special(
            state,
            "monster_decoy_triggered",
            monster,
            attacker,
            {"prevented_damage": damage},
        )
        state.event_log.append(f"{monster.role}'s decoy absorbs {attacker.role}'s blow.")
        return 0, f" {monster.role}'s decoy absorbs the blow."

    def _boss_incoming_damage_gate(
        self,
        state: GameState,
        attacker: Entity,
        monster: Entity,
        damage: int,
    ) -> tuple[int, str]:
        if not monster.equipment.get("boss"):
            return damage, ""
        counter_flag = monster.equipment.get("counter_flag")
        max_without_counter = monster.equipment.get("max_damage_without_counter")
        if (
            counter_flag
            and not state.scripts.get(str(counter_flag))
            and max_without_counter is not None
        ):
            capped = min(damage, int(max_without_counter))
            if capped < damage:
                state.trace.append(
                    {
                        "kind": "boss_special_used",
                        "round": state.round,
                        "monster_id": monster.id,
                        "role": monster.role,
                        "special": "counter_required",
                        "prevented_damage": damage - capped,
                        "attacker_id": attacker.id,
                    }
                )
                state.event_log.append(
                    f"{monster.role}'s boss ward turns aside the worst of the hit."
                )
                return (
                    capped,
                    f" {monster.role}'s boss ward caps the damage until its counterplay is found.",
                )
        return damage, ""

    def _apply_boss_phase_after_damage(
        self, state: GameState, monster: Entity, attacker: Entity
    ) -> str:
        if not monster.equipment.get("boss"):
            return ""
        phases = monster.equipment.get("phases")
        if not isinstance(phases, list):
            return ""
        triggered = set(str(item) for item in monster.equipment.get("triggered_phases", []))
        texts: list[str] = []
        for phase in phases:
            if not isinstance(phase, dict):
                continue
            phase_id = str(phase.get("id") or phase.get("phase") or "")
            if not phase_id or phase_id in triggered:
                continue
            threshold = int(phase.get("hp_at_or_below", phase.get("threshold", -1)))
            if threshold < 0 or monster.hp > threshold:
                continue
            triggered.add(phase_id)
            monster.equipment["triggered_phases"] = sorted(triggered)
            for status in phase.get("status", []):
                status = str(status)
                if status and status not in monster.status:
                    monster.status.append(status)
            if "attack_bonus" in phase:
                monster.equipment["phase_attack_bonus"] = int(
                    monster.equipment.get("phase_attack_bonus", 0)
                ) + int(phase["attack_bonus"])
            if "alert" in phase:
                state.alert += int(phase["alert"])
            if isinstance(phase.get("set_script"), dict):
                for key, value in phase["set_script"].items():
                    state.scripts[str(key)] = value
            message = str(phase.get("message") or f"{monster.role} enters {phase_id}.")
            texts.append(message)
            event = {
                "kind": "boss_phase_changed",
                "round": state.round,
                "monster_id": monster.id,
                "role": monster.role,
                "phase": phase_id,
                "hp": monster.hp,
                "attacker_id": attacker.id,
            }
            state.trace.append(event)
            state.event_log.append(message)
        return (" " + " ".join(texts)) if texts else ""

    def _maybe_revive_hollow_knight(
        self, state: GameState, monster: Entity, attacker: Entity
    ) -> bool:
        if monster.role != "hollow_knight":
            return False
        if attacker.equipment.get("charm") == "holy_charm":
            monster.status.append("banished")
            self._record_defensive_prevention(
                state,
                attacker,
                "holy_charm",
                "hollow_revive",
                {"monster_id": monster.id, "monster_role": monster.role},
            )
            state.event_log.append(f"{attacker.role}'s holy charm stills {monster.role}.")
            return False
        if "revived" in monster.status:
            return False
        counter_statuses = {"banished", "vulnerable", "hollow_banished"}
        if counter_statuses & set(monster.status):
            return False
        if state.scripts.get(f"{monster.id}_banished") or state.scripts.get(
            "hollow_knight_banished"
        ):
            return False
        monster.status.append("revived")
        monster.alive = True
        monster.hp = 1
        self._record_monster_special(
            state,
            "monster_revived",
            monster,
            attacker,
            {"restored_hp": 1},
        )
        state.event_log.append(f"{monster.role} rises again.")
        return True

    def _apply_hero_defense_prevention(
        self,
        state: GameState,
        hero: Entity,
        damage: int,
        *,
        source: str,
    ) -> tuple[int, str]:
        if damage <= 0:
            return damage, ""
        if "warded" in hero.status:
            hero.status.remove("warded")
            reduced = max(0, damage - 1)
            self._record_spell_status_triggered(
                state,
                hero,
                "ward_circle",
                "incoming_damage",
                {"prevented_damage": damage - reduced},
            )
            return reduced, " Ward circle absorbs 1 damage."
        if hero.equipment.get("helm") == "iron_helm" and source == "lethal" and damage >= hero.hp:
            reduced = max(0, hero.hp - 1)
            prevented = damage - reduced
            self._consume_equipped_item(hero, "helm")
            self._record_defensive_prevention(
                state,
                hero,
                "iron_helm",
                "lethal_hit",
                {"prevented_damage": prevented},
            )
            state.event_log.append(f"{hero.role}'s iron helm turns a lethal blow.")
            return reduced, " Iron helm turns the lethal blow."
        return damage, ""

    def _apply_cleave_defense_prevention(
        self, state: GameState, hero: Entity, damage: int
    ) -> tuple[int, str]:
        if damage <= 0:
            return damage, ""
        if hero.equipment.get("helm") == "iron_helm":
            self._consume_equipped_item(hero, "helm")
            self._record_defensive_prevention(
                state,
                hero,
                "iron_helm",
                "cleave",
                {"prevented_damage": damage},
            )
            state.event_log.append(f"{hero.role}'s iron helm catches the cleave.")
            return 0, f" {hero.role}'s iron helm catches the cleave."
        return damage, ""

    def _record_spell_status_triggered(
        self,
        state: GameState,
        hero: Entity,
        spell: str,
        trigger: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        event = {
            "kind": "spell_status_triggered",
            "round": state.round,
            "agent_id": hero.id,
            "role": hero.role,
            "spell": spell,
            "trigger": trigger,
            **dict(payload or {}),
        }
        state.trace.append(event)
        state.event_log.append(f"{hero.role}'s {spell} triggers.")

    def _consume_equipped_item(self, hero: Entity, slot: str) -> str | None:
        item_id = hero.equipment.pop(slot, None)
        self._refresh_equipment_stats(hero)
        return str(item_id) if item_id else None

    def _record_defensive_prevention(
        self,
        state: GameState,
        hero: Entity,
        item_id: str,
        prevented: str,
        payload: dict[str, Any] | None = None,
    ) -> None:
        state.trace.append(
            {
                "kind": "defensive_prevention",
                "round": state.round,
                "agent_id": hero.id,
                "role": hero.role,
                "item": item_id,
                "prevented": prevented,
                **dict(payload or {}),
            }
        )

    def _inspect_tile(self, state: GameState, hero: Entity, pos: Pos) -> tuple[str, float]:
        self._cost(state, hero, "inspect_tile")
        found: list[str] = []
        trap = state.trap_at(pos)
        if trap and trap.armed and not trap.revealed:
            trap.revealed = True
            found.append(f"trap {trap.id}")
        door = state.door_at(pos)
        if door and door.secret and not door.discovered:
            door.discovered = True
            found.append(f"secret door {door.id}")
        if found:
            return f"{hero.role} inspects the tile and finds " + ", ".join(found) + ".", 0.06
        return f"{hero.role} inspects the tile and finds nothing hidden.", 0.0

    def _inspect_room(self, state: GameState, hero: Entity) -> tuple[str, float]:
        self._cost(state, hero, "inspect_room")
        visible = self.grid.visible_tiles(state, hero.id)
        found: list[str] = []
        for trap in state.traps.values():
            if trap.pos in visible and trap.armed and not trap.revealed:
                trap.revealed = True
                found.append(trap.id)
        for door in state.doors.values():
            if door.pos in visible and door.secret and not door.discovered:
                door.discovered = True
                found.append(door.id)
        if found:
            return f"{hero.role} searches the area and reveals: {', '.join(found)}.", 0.08
        return f"{hero.role} searches the area but finds no hidden features.", 0.0

    def _search_traps(self, state: GameState, hero: Entity) -> tuple[str, float]:
        self._cost(state, hero, "search_traps")
        visible = self.grid.visible_tiles(state, hero.id)
        found: list[str] = []
        for trap in state.traps.values():
            if trap.pos in visible and trap.armed and not trap.revealed:
                trap.revealed = True
                found.append(trap.id)
        self._record_search(state, hero, "traps", found)
        if found:
            reward = 0.06 * len(found) + (0.02 if hero.role == "dwarf" else 0.0)
            return f"{hero.role} searches for traps and marks: {', '.join(found)}.", reward
        return f"{hero.role} searches for traps but finds none.", 0.0

    def _search_secrets(self, state: GameState, hero: Entity) -> tuple[str, float]:
        self._cost(state, hero, "search_secrets")
        visible = self.grid.visible_tiles(state, hero.id)
        found: list[str] = []
        for door in state.doors.values():
            if door.pos in visible and door.secret and not door.discovered:
                door.discovered = True
                found.append(door.id)
        self._record_search(state, hero, "secrets", found)
        if found:
            return f"{hero.role} searches for secrets and finds: {', '.join(found)}.", 0.08 * len(
                found
            )
        return f"{hero.role} searches for secrets but finds none.", 0.0

    def _disarm(self, state: GameState, hero: Entity, trap_id: str) -> tuple[str, float]:
        trap = state.traps[trap_id]
        self._cost(state, hero, "disarm")
        # Simple deterministic skill gate with random tie-breaker.
        roll = self.rng.randint(1, 6) + (2 if hero.role == "dwarf" else 0)
        if roll >= 4:
            trap.armed = False
            trap.revealed = True
            return f"{hero.role} disarms {trap.id}.", 0.08
        hero.hp -= 1
        state.total_damage_taken += 1
        trap.armed = False
        trap.revealed = True
        if hero.hp <= 0:
            hero.alive = False
            hero.hp = 0
        return f"{hero.role} fails to disarm {trap.id}; it triggers for 1 damage.", -0.15

    def _interact(self, state: GameState, hero: Entity, target_id: str) -> tuple[str, float]:
        self._cost(state, hero, "interact")
        if target_id == "escape":
            if state.objective.carrier == hero.id and hero.pos == state.escape_tile:
                state.objective.recovered = True
                state.done = True
                state.winner = "heroes"
                state.phase = "done"
                return f"{hero.role} exits with {state.objective.id}.", 1.0
            return f"{hero.role} cannot escape yet.", -0.1
        if target_id == state.objective.id:
            if (
                state.objective.carrier is None
                and state.objective.pos is not None
                and self.grid.manhattan(hero.pos, state.objective.pos) <= 1
            ):
                state.objective.carrier = hero.id
                state.objective.pos = None
                hero.inventory.append(state.objective.id)
                self._run_script(state, "on_objective_taken")
                return f"{hero.role} takes {state.objective.id}.", 0.25
            return f"{hero.role} cannot reach {state.objective.id}.", -0.1
        chest = state.chests.get(target_id)
        if chest and not chest.opened:
            chest.opened = True
            return self._open_chest(state, hero, chest.contents)
        furniture = state.furniture.get(target_id)
        if (
            furniture
            and not furniture.destroyed
            and "interact" not in furniture.searched_categories
            and self.grid.manhattan(hero.pos, furniture.pos) <= 1
        ):
            furniture.searched_categories.add("interact")
            return self._search_furniture(state, hero, furniture)
        return f"{hero.role} finds nothing useful to interact with.", -0.05

    def _search_treasure(self, state: GameState, hero: Entity, target_id: str) -> tuple[str, float]:
        self._cost(state, hero, "search_treasure")
        chest = state.chests.get(target_id)
        if chest and not chest.opened:
            chest.opened = True
            self._record_search(state, hero, "treasure", [target_id])
            text, reward = self._open_chest(state, hero, chest.contents)
            return text.replace("opens a chest", "searches a chest", 1), reward
        furniture = state.furniture.get(target_id)
        if (
            furniture
            and not furniture.destroyed
            and "treasure" not in furniture.searched_categories
        ):
            return self._search_furniture(state, hero, furniture, action_type="search_treasure")
        self._record_search(state, hero, "treasure", [])
        return f"{hero.role} searches for treasure but finds no searchable target.", -0.03

    def _search_furniture_target(
        self, state: GameState, hero: Entity, target_id: str
    ) -> tuple[str, float]:
        self._cost(state, hero, "search_furniture")
        furniture = state.furniture.get(target_id)
        if (
            furniture
            and not furniture.destroyed
            and "furniture" not in furniture.searched_categories
        ):
            return self._search_furniture(state, hero, furniture, action_type="search_furniture")
        self._record_search(state, hero, "furniture", [])
        return f"{hero.role} searches furniture but finds no searchable target.", -0.03

    def _search_furniture(
        self,
        state: GameState,
        hero: Entity,
        furniture,
        *,
        action_type: str = "interact",
    ) -> tuple[str, float]:
        category = "treasure" if action_type == "search_treasure" else "furniture"
        furniture.searched_categories.add(category)
        furniture.searched = bool(furniture.searched_categories)
        effect = furniture.search_effects.get(category)
        if effect is None:
            effect = {"type": "draw_deck", "deck": furniture.deck or "treasure"}
        effect_text, effect_reward, effect_result = self._resolve_furniture_effect(
            state,
            hero,
            furniture,
            effect,
            trigger=f"search_{category}",
        )
        event = self._record_furniture_event(
            state,
            hero,
            "furniture_searched",
            furniture,
            category=category,
            effect_result=effect_result,
        )
        self._record_search(state, hero, category, [furniture.id])
        state.scripts["_last_furniture_result"] = event
        if effect_text:
            return f"{hero.role} searches {furniture.name}. {effect_text}", effect_reward
        return f"{hero.role} searches {furniture.name} but finds only dust.", 0.02 + effect_reward

    def _attack_object(self, state: GameState, hero: Entity, target_id: str) -> tuple[str, float]:
        furniture = state.furniture[target_id]
        self._cost(state, hero, "attack_object")
        attack_dice = self._attack_dice(hero, ranged=False)
        hits = max(1, self._roll_successes(attack_dice))
        furniture.hp = max(0, furniture.hp - hits)
        text = f"{hero.role} strikes {furniture.name} for {hits} damage."
        reward = 0.02 * hits
        result: dict[str, Any] = {"damage": hits, "destroyed": False}
        if furniture.hp <= 0 and not furniture.destroyed:
            furniture.destroyed = True
            result["destroyed"] = True
            effect_text, effect_reward, effect_result = self._resolve_furniture_effect(
                state,
                hero,
                furniture,
                furniture.break_effect,
                trigger="destroy",
            )
            result["effect"] = effect_result
            reward += 0.05 + effect_reward
            text += f" {furniture.name} breaks apart."
            if effect_text:
                text += f" {effect_text}"
        event = self._record_furniture_event(
            state,
            hero,
            "furniture_destroyed" if furniture.destroyed else "furniture_damaged",
            furniture,
            category="destroy",
            effect_result=result,
        )
        state.scripts["_last_furniture_result"] = event
        return text, reward

    def _resolve_furniture_effect(
        self,
        state: GameState,
        hero: Entity,
        furniture,
        effect: Any,
        *,
        trigger: str,
    ) -> tuple[str, float, dict[str, Any]]:
        if effect is None:
            return "", 0.0, {"trigger": trigger, "effects": []}
        effects = effect if isinstance(effect, list) else [effect]
        texts: list[str] = []
        reward = 0.0
        resolved: list[dict[str, Any]] = []
        for raw in effects:
            payload = (
                {"type": "draw_deck", "deck": furniture.deck or "treasure"}
                if raw == "draw_deck"
                else raw
            )
            if isinstance(payload, str):
                payload = {"type": payload}
            if not isinstance(payload, dict):
                continue
            kind = str(payload.get("type", "emit"))
            item = str(payload.get("item", ""))
            if kind == "draw_deck":
                card = self._draw_card(
                    state, str(payload.get("deck", furniture.deck or "treasure"))
                )
                if card:
                    card_text, card_reward = self._resolve_furniture_card(
                        state, hero, furniture, card
                    )
                    texts.append(card_text)
                    reward += card_reward
                    resolved.append({"type": "card", "card": dict(card)})
                else:
                    resolved.append({"type": "card", "card": None})
            elif kind in {"item", "weapon", "armor", "artifact", "spell"} and item:
                if kind == "spell":
                    cards = hero.equipment.setdefault("spell_cards", [])
                    if item not in cards:
                        cards.append(item)
                    item_name = SPELL_CARDS.get(item, {}).get("name", item)
                    texts.append(f"{hero.role} learns {item_name}.")
                else:
                    hero.inventory.append(item)
                    item_name = (WEAPON_ITEMS.get(item) or ARMOR_ITEMS.get(item) or {}).get(
                        "name", item
                    )
                    texts.append(f"{hero.role} gains {item_name}.")
                reward += float(payload.get("reward", 0.1))
                resolved.append({"type": kind, "item": item})
            elif kind in {"gold", "treasure"}:
                amount = int(payload.get("amount", payload.get("treasure", 1)))
                state.treasure_collected += amount
                hero.inventory.append("coin_cache")
                texts.append(f"{hero.role} finds {amount} gold cache{'s' if amount != 1 else ''}.")
                reward += float(payload.get("reward", 0.1 * amount))
                resolved.append({"type": "gold", "amount": amount})
            elif kind == "alert":
                amount = int(payload.get("amount", payload.get("alert", 1)))
                state.alert += amount
                texts.append(f"Alert rises by {amount}.")
                reward += float(payload.get("reward", -0.03 * amount))
                resolved.append({"type": "alert", "amount": amount})
            elif kind == "damage":
                amount = int(payload.get("amount", payload.get("damage", 1)))
                hero.hp = max(0, hero.hp - amount)
                state.total_damage_taken += amount
                if hero.hp <= 0:
                    hero.alive = False
                texts.append(f"{hero.role} takes {amount} damage.")
                reward += float(payload.get("reward", -0.15 * amount))
                resolved.append({"type": "damage", "amount": amount})
            elif kind == "heal":
                amount = int(payload.get("amount", payload.get("heal", 1)))
                healed = min(amount, hero.max_hp - hero.hp)
                hero.hp += healed
                texts.append(f"{hero.role} restores {healed} hp.")
                reward += float(payload.get("reward", 0.06 * healed))
                resolved.append({"type": "heal", "amount": healed})
            elif kind in {"lower_alert", "suppress_alert"}:
                amount = int(payload.get("amount", payload.get("alert", 1)))
                old_alert = state.alert
                state.alert = max(0, state.alert - amount)
                texts.append(f"Alert falls from {old_alert} to {state.alert}.")
                reward += float(payload.get("reward", 0.03 * (old_alert - state.alert)))
                resolved.append({"type": "lower_alert", "amount": old_alert - state.alert})
            elif kind == "hero_status":
                status = str(payload.get("status", ""))
                if status and status not in hero.status:
                    hero.status.append(status)
                if status:
                    texts.append(f"{hero.role} gains {status}.")
                    resolved.append({"type": "hero_status", "status": status})
            elif kind == "set_script":
                key = str(payload.get("key", ""))
                if key:
                    state.scripts[key] = payload.get("value", True)
                    resolved.append({"type": "set_script", "key": key, "value": state.scripts[key]})
            elif kind == "reveal":
                found = self._reveal_glyphs_near(state, hero)
                if found:
                    texts.append(f"Revealed: {', '.join(found)}.")
                else:
                    texts.append("No hidden marks answer.")
                resolved.append({"type": "reveal", "found": found})
            elif kind == "monster_status":
                status = str(payload.get("status", ""))
                target = self._effect_target_monsters(state, payload)
                for monster in target:
                    if status and status not in monster.status:
                        monster.status.append(status)
                if target and status:
                    texts.append(
                        f"{status.title()} marked on {', '.join(monster.id for monster in target)}."
                    )
                    resolved.append(
                        {
                            "type": "monster_status",
                            "status": status,
                            "targets": [m.id for m in target],
                        }
                    )
            elif kind == "spawn_monster":
                monster_id = str(payload.get("id", ""))
                role = str(payload.get("role", "skitterling"))
                pos_raw = payload.get("pos")
                pos = (
                    tuple(pos_raw)
                    if isinstance(pos_raw, list) and len(pos_raw) == 2
                    else self._nearest_free_adjacent(state, hero.pos)
                )
                if (
                    monster_id
                    and role in MONSTER_TYPES
                    and pos
                    and monster_id not in state.monsters
                ):
                    spec = MONSTER_TYPES[role]
                    state.monsters[monster_id] = Entity(
                        id=monster_id,
                        team="dungeon",
                        role=role,
                        hp=spec["hp"],
                        max_hp=spec["hp"],
                        attack=spec["attack"],
                        guard=spec["guard"],
                        speed=spec["speed"],
                        behavior=spec["behavior"],
                        pos=pos,
                        activation="engaged",
                        room_id=self.grid.room_id_at(state.rooms, pos),
                    )
                    texts.append(f"{role} appears.")
                    resolved.append({"type": "spawn_monster", "id": monster_id, "role": role})
            elif kind == "activate_monster":
                target = self._effect_target_monsters(state, payload)
                for monster in target:
                    monster.activation = "engaged"
                if target:
                    texts.append(f"{', '.join(monster.id for monster in target)} stir.")
                    resolved.append({"type": "activate_monster", "targets": [m.id for m in target]})
            elif kind == "emit":
                message = str(payload.get("message", ""))
                if message:
                    texts.append(message)
                    state.event_log.append(message)
                    resolved.append({"type": "emit", "message": message})
            trace_kind = payload.get("trace_kind")
            if trace_kind:
                state.trace.append(
                    {
                        "kind": str(trace_kind),
                        "round": state.round,
                        "agent_id": hero.id,
                        "furniture_id": furniture.id,
                        "effect_type": kind,
                    }
                )
        result = {"trigger": trigger, "effects": resolved}
        state.trace.append(
            {
                "kind": "furniture_effect_resolved",
                "round": state.round,
                "agent_id": hero.id,
                "furniture_id": furniture.id,
                **result,
            }
        )
        return " ".join(texts), reward, result

    def _resolve_furniture_card(
        self, state: GameState, hero: Entity, furniture, card: dict[str, Any]
    ) -> tuple[str, float]:
        reward = float(card.get("reward", 0.05))
        name = card.get("name", card.get("id", "a card"))
        texts = [f"Draws {name}."]
        effects = list(card.get("effects", [])) if isinstance(card.get("effects"), list) else []
        card_type = str(card.get("type", "treasure"))
        item = card.get("item")
        if item:
            if card_type == "spell":
                effects.append({"type": "spell", "item": item})
            elif card_type == "armor":
                effects.append({"type": "armor", "item": item})
            elif card_type in {"weapon", "artifact", "healing"}:
                effects.append({"type": card_type, "item": item})
            elif card_type != "event":
                effects.append({"type": "item", "item": item})
        if "treasure" in card:
            effects.append({"type": "gold", "amount": card.get("treasure", 1), "reward": 0.0})
        if "alert" in card:
            effects.append({"type": "alert", "amount": card.get("alert", 1), "reward": 0.0})
        if "heal" in card:
            effects.append({"type": "heal", "amount": card.get("heal"), "reward": 0.0})
        if not effects and card_type == "healing":
            effects.append({"type": "item", "item": "healing_draught"})
        if effects:
            effect_text, effect_reward, _ = self._resolve_furniture_effect(
                state,
                hero,
                furniture,
                effects,
                trigger=f"card:{card.get('id', name)}",
            )
            if effect_text:
                texts.append(effect_text)
            reward += effect_reward
        return " ".join(texts), reward

    def _effect_target_monsters(self, state: GameState, payload: dict[str, Any]) -> list[Entity]:
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

    def _record_furniture_event(
        self,
        state: GameState,
        hero: Entity,
        kind: str,
        furniture,
        *,
        category: str,
        effect_result: dict[str, Any],
    ) -> dict[str, Any]:
        event = {
            "kind": kind,
            "round": state.round,
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
        state.trace.append(event)
        state.event_log.append(f"{hero.role} {category} {furniture.name}.")
        return event

    def _record_search(
        self, state: GameState, hero: Entity, category: str, found: list[str]
    ) -> None:
        event = {
            "kind": "search",
            "round": state.round,
            "agent_id": hero.id,
            "role": hero.role,
            "category": category,
            "found": list(found),
        }
        state.trace.append(event)
        if found:
            state.event_log.append(f"{hero.role} search {category}: {', '.join(found)}")

    def _draw_card(self, state: GameState, deck_id: str) -> dict[str, Any] | None:
        deck = state.decks.get(deck_id)
        if not deck:
            if self._deck_policy(state, deck_id).get("reshuffle") and state.discards.get(deck_id):
                state.decks[deck_id] = list(state.discards.get(deck_id, []))
                self.rng.shuffle(state.decks[deck_id])
                state.discards[deck_id] = []
                state.trace.append(
                    {"kind": "deck_reshuffled", "round": state.round, "deck": deck_id}
                )
                state.event_log.append(f"The {deck_id} deck is reshuffled.")
                deck = state.decks.get(deck_id)
            else:
                state.trace.append(
                    {"kind": "deck_exhausted", "round": state.round, "deck": deck_id}
                )
                state.event_log.append(f"The {deck_id} deck is exhausted.")
        if not deck:
            return None
        card = deck.pop(0)
        state.discards.setdefault(deck_id, []).append(card)
        state.trace.append(
            {
                "kind": "card_draw",
                "round": state.round,
                "deck": deck_id,
                "card": dict(card),
                "card_id": card.get("id"),
                "card_type": card.get("type"),
                "rarity": card.get("rarity", "common"),
            }
        )
        state.event_log.append(
            f"Card drawn from {deck_id}: {card.get('name', card.get('id', 'unknown card'))}."
        )
        return card

    def _deck_policy(self, state: GameState, deck_id: str) -> dict[str, Any]:
        policies = state.scripts.get("deck_policies", {})
        if isinstance(policies, dict) and isinstance(policies.get(deck_id), dict):
            return dict(policies[deck_id])
        if deck_id == "event":
            return {"reshuffle": True}
        return {"reshuffle": False}

    def _use_item(self, state: GameState, hero: Entity, item_id: str) -> tuple[str, float]:
        self._cost(state, hero, "use_item")
        if item_id == "healing_draught" and item_id in hero.inventory:
            hero.inventory.remove(item_id)
            amount = min(3, hero.max_hp - hero.hp)
            hero.hp += amount
            return f"{hero.role} drinks a healing draught and restores {amount} hp.", 0.08 * amount
        if item_id == "lantern_lens" and item_id in hero.inventory:
            if "lantern_lens_active" not in hero.status:
                hero.status.append("lantern_lens_active")
            state.torch = min(24, state.torch + 2)
            return f"{hero.role} raises the lantern lens; the party's light steadies.", 0.06
        return f"{hero.role} cannot use {item_id} right now.", -0.05

    def _equip_item(self, state: GameState, hero: Entity, item_id: str) -> tuple[str, float]:
        self._cost(state, hero, "equip_item")
        if item_id not in hero.inventory:
            return f"{hero.role} does not carry {item_id}.", -0.05
        if not self._is_equippable(item_id):
            return f"{hero.role} cannot equip {item_id}.", -0.05
        if not self._can_equip(hero, item_id):
            return f"{hero.role} cannot use {self._item_name(item_id)}.", -0.05
        slot = self._item_slot(item_id)
        previous = hero.equipment.get(slot)
        if previous and self._is_equippable(str(previous)) and previous not in hero.inventory:
            hero.inventory.append(str(previous))
        hero.inventory.remove(item_id)
        hero.equipment[slot] = item_id
        self._refresh_equipment_stats(hero)
        event = {
            "kind": "item_equipped",
            "round": state.round,
            "agent_id": hero.id,
            "role": hero.role,
            "item": item_id,
            "slot": slot,
            "item_type": "weapon" if item_id in WEAPON_ITEMS else "armor",
        }
        state.trace.append(event)
        if item_id in ARMOR_ITEMS:
            state.trace.append({**event, "kind": "armor_equipped"})
        state.event_log.append(f"{hero.role} equips {self._item_name(item_id)}.")
        return f"{hero.role} equips {self._item_name(item_id)}.", 0.04

    def _give_item(
        self, state: GameState, hero: Entity, target_id: str, payload: dict[str, Any]
    ) -> tuple[str, float]:
        self._cost(state, hero, "give_item")
        item_id = str((payload or {}).get("item", "")).strip()
        target = state.heroes.get(target_id)
        if not item_id:
            return f"{hero.role} must choose an item to give.", -0.05
        if not target:
            return f"{hero.role} cannot find hero {target_id}.", -0.05
        if not target.alive:
            return f"{hero.role} cannot give {item_id} to a downed hero.", -0.05
        if self.grid.manhattan(hero.pos, target.pos) > 1:
            return f"{target.role} is not adjacent for an item handoff.", -0.05
        if item_id == state.objective.id:
            return f"{hero.role} cannot hand off the objective item this way.", -0.05
        if item_id not in hero.inventory:
            return f"{hero.role} does not carry {item_id}.", -0.05
        hero.inventory.remove(item_id)
        target.inventory.append(item_id)
        event = {
            "kind": "item_given",
            "round": state.round,
            "agent_id": hero.id,
            "role": hero.role,
            "target_agent_id": target.id,
            "target_role": target.role,
            "item": item_id,
        }
        state.trace.append(event)
        state.event_log.append(f"{hero.role} gives {item_id} to {target.role}.")
        return f"{hero.role} gives {item_id} to {target.role}.", 0.02

    def _open_chest(self, state: GameState, hero: Entity, contents: Any) -> tuple[str, float]:
        if isinstance(contents, list):
            total_reward = 0.0
            texts: list[str] = []
            for item in contents:
                text, reward = self._open_chest(state, hero, item)
                texts.append(text)
                total_reward += reward
            return " ".join(texts), total_reward
        if isinstance(contents, dict):
            return self._open_chest_payload(state, hero, contents)
        if contents in {"coin_cache", "treasure"}:
            state.treasure_collected += 1
            hero.inventory.append("coin_cache")
            return f"{hero.role} opens a chest and collects a small coin cache.", 0.1
        if contents == "healing_draught":
            hero.inventory.append("healing_draught")
            return f"{hero.role} opens a chest and finds a healing draught.", 0.08
        if contents in WEAPON_ITEMS or contents in ARMOR_ITEMS:
            hero.inventory.append(str(contents))
            return f"{hero.role} opens a chest and finds {self._item_name(str(contents))}.", 0.12
        if contents == "shrine_token":
            hero.inventory.append("shrine_token")
            tokens = sum(h.inventory.count("shrine_token") for h in state.heroes.values())
            required = int(state.scripts.get("token_requirement", 2))
            if tokens >= required:
                for door in state.doors.values():
                    if list(door.pos) == state.scripts.get("locked_shrine_door"):
                        door.state = "open"
                        door.discovered = True
            return f"{hero.role} opens a chest and finds a shrine token.", 0.12
        if contents == "ambush":
            pos = self._nearest_free_adjacent(state, hero.pos)
            if pos:
                count = len([m for m in state.monsters if m.startswith("skitterling_")]) + 1
                spec = {"hp": 1, "attack": 1, "guard": 1, "speed": 4, "behavior": "swarm_nearest"}
                monster_id = f"skitterling_{count}"
                state.monsters[monster_id] = Entity(
                    id=monster_id,
                    team="dungeon",
                    role="skitterling",
                    hp=spec["hp"],
                    max_hp=spec["hp"],
                    attack=spec["attack"],
                    guard=spec["guard"],
                    speed=spec["speed"],
                    behavior=spec["behavior"],
                    pos=pos,
                    activation="engaged",
                    room_id=self.grid.room_id_at(state.rooms, pos),
                )
            return f"{hero.role} opens a chest; a skitterling ambush bursts out.", -0.05
        if isinstance(contents, str) and contents:
            hero.inventory.append(contents)
            return f"{hero.role} opens a chest and finds {contents}.", 0.08
        return f"{hero.role} opens a chest; it is empty.", 0.0

    def _open_chest_payload(
        self, state: GameState, hero: Entity, payload: dict[str, Any]
    ) -> tuple[str, float]:
        payload_type = str(payload.get("type", "item"))
        if payload_type == "table":
            entries = list(payload.get("entries", []))
            if not entries:
                return f"{hero.role} opens a chest; it is empty.", 0.0
            return self._open_chest(state, hero, self.rng.choice(entries))
        if payload_type == "bundle":
            return self._open_chest(state, hero, list(payload.get("contents", [])))
        if payload_type in {"gold", "treasure"}:
            amount = int(payload.get("amount", payload.get("treasure", 1)))
            state.treasure_collected += amount
            hero.inventory.append("coin_cache")
            return (
                f"{hero.role} opens a chest and finds {amount} gold cache{'s' if amount != 1 else ''}.",
                0.1 * amount,
            )
        if payload_type == "weapon":
            item = str(payload.get("item", ""))
            if item in WEAPON_ITEMS:
                hero.inventory.append(item)
                return f"{hero.role} opens a chest and finds {WEAPON_ITEMS[item]['name']}.", float(
                    payload.get("reward", 0.14)
                )
            return f"{hero.role} opens a chest and finds an unfamiliar weapon.", 0.02
        if payload_type == "armor":
            item = str(payload.get("item", ""))
            if item in ARMOR_ITEMS:
                hero.inventory.append(item)
                return f"{hero.role} opens a chest and finds {ARMOR_ITEMS[item]['name']}.", float(
                    payload.get("reward", 0.12)
                )
            return f"{hero.role} opens a chest and finds unfamiliar armor.", 0.02
        if payload_type == "spell":
            item = str(payload.get("item", payload.get("spell", "")))
            if item in SPELL_CARDS:
                hero.equipment.setdefault("spell_cards", []).append(item)
                return (
                    f"{hero.role} opens a chest and finds the {SPELL_CARDS[item]['name']} spell card.",
                    float(payload.get("reward", 0.12)),
                )
            return f"{hero.role} opens a chest and finds an unreadable spell card.", 0.02
        if payload_type == "draw_deck":
            deck_id = str(payload.get("deck", "treasure"))
            card = self._draw_card(state, deck_id)
            if card:
                text, reward = self._resolve_furniture_card(
                    state,
                    hero,
                    type(
                        "ChestCardSource", (), {"id": "chest", "deck": deck_id, "name": "Chest"}
                    )(),
                    card,
                )
                return f"{hero.role} opens a chest. {text}", reward
            return f"{hero.role} opens a chest, but the {deck_id} deck is empty.", 0.0
        if payload_type == "item":
            item = str(payload.get("item", payload.get("id", "")))
            if item:
                hero.inventory.append(item)
                return f"{hero.role} opens a chest and finds {item}.", float(
                    payload.get("reward", 0.08)
                )
        if payload_type == "trap":
            damage = int(payload.get("damage", 1))
            hero.hp = max(0, hero.hp - damage)
            state.total_damage_taken += damage
            if hero.hp <= 0:
                hero.alive = False
            return (
                f"{hero.role} opens a chest; a trap snaps shut for {damage} damage.",
                -0.15 * damage,
            )
        if payload_type == "ambush":
            return self._open_chest(state, hero, "ambush")
        return f"{hero.role} opens a chest; it is empty.", 0.0

    def _can_equip(self, hero: Entity, item_id: str) -> bool:
        item = WEAPON_ITEMS.get(item_id) or ARMOR_ITEMS.get(item_id)
        if not item:
            return False
        roles = item.get("roles")
        return not roles or hero.role in set(roles)

    def _is_equippable(self, item_id: str) -> bool:
        return item_id in WEAPON_ITEMS or item_id in ARMOR_ITEMS

    def _item_slot(self, item_id: str) -> str:
        if item_id in WEAPON_ITEMS:
            return "weapon"
        return str(ARMOR_ITEMS.get(item_id, {}).get("slot", "item"))

    def _item_name(self, item_id: str) -> str:
        return str(
            (WEAPON_ITEMS.get(item_id) or ARMOR_ITEMS.get(item_id) or {}).get("name", item_id)
        )

    def _refresh_equipment_stats(self, hero: Entity) -> None:
        base = HERO_ARCHETYPES.get(hero.role, {})
        hero.speed = max(
            1, int(base.get("speed", hero.speed)) + self._equipment_speed_modifier(hero)
        )

    def _equipment_speed_modifier(self, hero: Entity) -> int:
        return sum(
            int(ARMOR_ITEMS.get(str(item_id), {}).get("speed", 0))
            for slot, item_id in hero.equipment.items()
            if slot != "weapon"
        )

    def _hero_guard(self, hero: Entity, *, ranged: bool = False) -> int:
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

    def _equipped_weapon(self, hero: Entity) -> dict[str, Any] | None:
        item_id = hero.equipment.get("weapon")
        return WEAPON_ITEMS.get(str(item_id)) if item_id else None

    def _weapon_range(self, hero: Entity) -> int:
        weapon = self._equipped_weapon(hero)
        if not weapon:
            return 5 if hero.role == "wizard" else 1
        if "ranged_dice" in weapon:
            return int(weapon.get("range", 1))
        return 5 if hero.role == "wizard" else int(weapon.get("range", 1))

    def _attack_dice(self, attacker: Entity, *, ranged: bool) -> int:
        weapon = self._equipped_weapon(attacker)
        if ranged:
            if weapon and "ranged_dice" in weapon:
                return max(1, int(weapon["ranged_dice"]))
            if attacker.role == "wizard":
                focus_bonus = int(weapon.get("focus_bonus", 0)) if weapon else 0
                return max(2, (attacker.focus + focus_bonus) // 2)
            return max(1, attacker.attack - 1)
        if weapon and "melee_dice" in weapon:
            return max(1, int(weapon["melee_dice"]))
        return max(1, attacker.attack)

    def _guard(self, state: GameState, hero: Entity) -> tuple[str, float]:
        if "guarded" not in hero.status:
            hero.status.append("guarded")
        self._cost(state, hero, "guard")
        return f"{hero.role} takes a guarded stance.", 0.01

    def _warden_auto(self, state: GameState) -> tuple[float, str]:
        texts: list[str] = []
        reward = -0.01
        for monster_id in list(state.monsters):
            monster = state.monsters[monster_id]
            if not monster.alive or monster.activation == "dormant":
                continue
            extra, text = self._activate_monster(state, monster_id)
            reward += extra
            if text:
                texts.append(text)
        if not texts:
            texts.append("The dungeon stirs, but no monster reaches the heroes.")
        self._check_end_conditions(state)
        return reward, " ".join(texts)

    def _activate_monster(self, state: GameState, monster_id: str) -> tuple[float, str]:
        monster = state.monsters.get(monster_id)
        if not monster or not monster.alive:
            return 0.0, ""
        heroes = [h for h in state.heroes.values() if h.alive]
        if not heroes:
            return 0.0, ""
        adjacent = [h for h in heroes if self.grid.manhattan(monster.pos, h.pos) == 1]
        if adjacent:
            monster.activation = "engaged"
            target = min(adjacent, key=lambda h: h.hp)
            text, reward = self._monster_attack(state, monster, target)
            return reward, text
        visible_targets = [
            h
            for h in heroes
            if self.grid.manhattan(monster.pos, h.pos) <= monster.sight_range
            and self.grid.line_clear(state, monster.pos, h.pos)
        ]
        if monster.role == "cinder_mage" and visible_targets:
            attack_range = int(getattr(monster, "equipment", {}).get("attack_range", 0) or 5)
            ranged_targets = [
                h
                for h in visible_targets
                if self.grid.manhattan(monster.pos, h.pos) <= attack_range
            ]
            if ranged_targets:
                monster.activation = "engaged"
                target = min(
                    ranged_targets, key=lambda h: (h.hp, self.grid.manhattan(monster.pos, h.pos))
                )
                text, reward = self._monster_attack(state, monster, target, ranged=True)
                state.alert += 1
                return reward - 0.01, text + " Cinders flare; alert rises."
        if visible_targets:
            monster.activation = "engaged"
        if monster.behavior == "hunt_objective_carrier" and state.objective.carrier in state.heroes:
            target = state.heroes[state.objective.carrier]
        else:
            target_pool = visible_targets or heroes
            target = min(target_pool, key=lambda h: self.grid.manhattan(monster.pos, h.pos))
        path = self.grid.find_path(state, monster.pos, target.pos, ignore_entities=True)
        if len(path) > 1:
            # Move up to speed tiles, stopping before occupied target.
            old = monster.pos
            steps = min(monster.speed, max(1, len(path) - 2))
            for candidate in path[1 : 1 + steps]:
                if state.entity_at(candidate):
                    break
                monster.pos = candidate
            if monster.pos != old:
                return -0.02, f"{monster.role} advances toward {target.role}."
        return 0.0, f"{monster.role} cannot find a route."

    def _monster_attack(
        self, state: GameState, monster: Entity, hero: Entity, *, ranged: bool = False
    ) -> tuple[str, float]:
        attack_dice = monster.attack + int(monster.equipment.get("phase_attack_bonus", 0))
        attack_dice = max(1, attack_dice - (1 if "weakened" in monster.status else 0))
        special_parts: list[str] = []
        if monster.equipment.get("boss") and monster.equipment.get("phase_attack_bonus"):
            special_parts.append(f"{monster.role}'s boss phase bears down.")
        if monster.role == "rat_pack" and self._hero_is_isolated(state, hero):
            attack_dice += 1
            self._record_monster_special(
                state,
                "monster_special_used",
                monster,
                hero,
                {"special": "isolation_swarm", "attack_bonus": 1},
                mirror_generic=False,
            )
            special_parts.append(f"{monster.role} surges at isolated {hero.role}.")
        if ranged:
            self._record_monster_special(
                state,
                "monster_ranged_attack",
                monster,
                hero,
                {"range": self.grid.manhattan(monster.pos, hero.pos)},
            )
        hits = self._roll_successes(attack_dice)
        blocks = self._roll_successes(
            self._hero_guard(hero, ranged=ranged) + (1 if "guarded" in hero.status else 0)
        )
        if "guarded" in hero.status:
            hero.status.remove("guarded")
        damage = max(0, hits - blocks)
        quiet_text = ""
        if damage > 0 and "quiet_step" in hero.status:
            hero.status.remove("quiet_step")
            reduced = max(0, damage - 1)
            self._record_spell_status_triggered(
                state,
                hero,
                "quiet_step",
                "monster_pressure",
                {"prevented_damage": damage - reduced, "monster_id": monster.id},
            )
            damage = reduced
            quiet_text = " Quiet step blunts the pressure."
        damage, prevention_text = self._apply_hero_defense_prevention(
            state, hero, damage, source="lethal"
        )
        hero.hp -= damage
        state.total_damage_taken += damage
        if hero.hp <= 0:
            hero.hp = 0
            hero.alive = False
            if state.objective.carrier == hero.id:
                if state.objective.fragile:
                    state.done = True
                    state.winner = "dungeon"
                    state.phase = "done"
                else:
                    state.objective.carrier = None
                    state.objective.pos = hero.pos
                    hero.inventory = [item for item in hero.inventory if item != state.objective.id]
        cleave_text = ""
        if monster.role == "tusk_mauler" and damage > 0:
            cleave_text = self._apply_tusk_cleave(state, monster, hero)
        mode = " at range" if ranged else ""
        prefix = " ".join(special_parts)
        if prefix:
            prefix += " "
        text = f"{prefix}{monster.role} attacks{mode} {hero.role}: {hits} hits, {blocks} blocks, {damage} damage."
        text += quiet_text
        text += prevention_text
        text += cleave_text
        if not hero.alive:
            text += f" {hero.role} is downed."
        return text, -0.1 * damage

    def _hero_is_isolated(self, state: GameState, hero: Entity) -> bool:
        return not any(
            ally.id != hero.id and ally.alive and self.grid.manhattan(hero.pos, ally.pos) <= 2
            for ally in state.heroes.values()
        )

    def _apply_tusk_cleave(self, state: GameState, monster: Entity, primary: Entity) -> str:
        adjacent = [
            hero
            for hero in state.heroes.values()
            if hero.id != primary.id
            and hero.alive
            and self.grid.manhattan(monster.pos, hero.pos) == 1
        ]
        if not adjacent:
            return ""
        target = min(adjacent, key=lambda h: h.hp)
        damage, prevention_text = self._apply_cleave_defense_prevention(state, target, 1)
        target.hp -= damage
        state.total_damage_taken += damage
        if target.hp <= 0:
            target.hp = 0
            target.alive = False
        self._record_monster_special(
            state,
            "monster_cleave",
            monster,
            target,
            {"primary_target": primary.id, "cleave_damage": damage},
        )
        state.event_log.append(f"{monster.role} cleaves into {target.role}.")
        suffix = f" {monster.role} cleaves into {target.role} for {damage} damage."
        suffix += prevention_text
        if not target.alive:
            suffix += f" {target.role} is downed."
        return suffix

    def _record_monster_special(
        self,
        state: GameState,
        kind: str,
        monster: Entity,
        hero: Entity | None = None,
        payload: dict[str, Any] | None = None,
        *,
        mirror_generic: bool = True,
    ) -> None:
        payload = dict(payload or {})
        event = {
            "kind": kind,
            "round": state.round,
            "monster_id": monster.id,
            "role": monster.role,
            **payload,
        }
        if hero:
            event["hero_id"] = hero.id
            event["hero_role"] = hero.role
        state.trace.append(event)
        if mirror_generic and kind != "monster_special_used":
            generic = {
                "kind": "monster_special_used",
                "round": state.round,
                "monster_id": monster.id,
                "role": monster.role,
                "special": kind.removeprefix("monster_"),
            }
            if hero:
                generic["hero_id"] = hero.id
                generic["hero_role"] = hero.role
            state.trace.append(generic)

    def _end_warden_phase(self, state: GameState) -> None:
        if state.done:
            return
        state.round += 1
        state.torch = max(0, state.torch - 1)
        state.phase = "hero"
        state.turn_index = 0
        for hero_id, hero in state.heroes.items():
            state.ap_remaining[hero_id] = 3 if hero.alive else 0
            if "guarded" in hero.status:
                hero.status.remove("guarded")
        self._skip_downed_heroes(state)
        self._run_script(state, "end_phase")
        self._check_end_conditions(state)

    def _advance_hero_turn(self, state: GameState) -> None:
        if state.done:
            return
        state.turn_index += 1
        self._skip_downed_heroes(state)
        if state.turn_index >= len(state.hero_order):
            state.phase = "warden"
            state.turn_index = 0

    def _skip_downed_heroes(self, state: GameState) -> None:
        while state.phase == "hero" and state.turn_index < len(state.hero_order):
            hero_id = state.hero_order[state.turn_index]
            if state.heroes[hero_id].alive:
                break
            state.turn_index += 1
        if state.phase == "hero" and state.turn_index >= len(state.hero_order):
            state.phase = "warden"
            state.turn_index = 0

    def _check_end_conditions(self, state: GameState) -> None:
        if state.done:
            state.phase = "done"
            return
        if not state.living_heroes():
            state.done = True
            state.winner = "dungeon"
            state.phase = "done"
            return
        if state.objective.recovered:
            state.done = True
            state.winner = "heroes"
            state.phase = "done"
            return

    def _roll_successes(self, dice: int) -> int:
        return sum(1 for _ in range(max(0, dice)) if self.rng.randint(1, 6) >= 5)

    def _run_script(self, state: GameState, script_name: str) -> None:
        script = state.scripts.get(script_name)
        if not script:
            return
        message = script.get("message")
        if message:
            state.event_log.append(message)
        for effect in script.get("effects", []):
            if effect.get("type") == "increase_alert":
                state.alert += int(effect.get("amount", 1))
            elif effect.get("type") == "spawn":
                role = effect.get("monster", "skitterling")
                pos = tuple(effect.get("pos"))
                if state.entity_at(pos) is None and self.grid.is_walkable(state, pos):
                    idx = len([m for m in state.monsters if m.startswith(f"{role}_")]) + 1
                    from .data import MONSTER_TYPES

                    spec = MONSTER_TYPES[role]
                    state.monsters[f"{role}_{idx}"] = Entity(
                        id=f"{role}_{idx}",
                        team="dungeon",
                        role=role,
                        hp=spec["hp"],
                        max_hp=spec["hp"],
                        attack=spec["attack"],
                        guard=spec["guard"],
                        speed=spec["speed"],
                        behavior=spec["behavior"],
                        pos=pos,  # type: ignore[arg-type]
                    )

    def _nearest_free_adjacent(self, state: GameState, pos: Pos) -> Pos | None:
        for candidate in self.grid.adjacent_positions(pos):
            if self.grid.is_walkable(state, candidate):
                return candidate
        return None

    def _pos_from_target(self, target: Any, default: Pos) -> Pos:
        if isinstance(target, (list, tuple)) and len(target) == 2:
            return int(target[0]), int(target[1])
        return default
