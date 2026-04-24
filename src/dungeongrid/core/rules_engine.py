"""RulesEngine: legal actions, action resolution, combat, turn order, reward."""

from __future__ import annotations

import random
from typing import Any, Optional

from .data import ACTION_COSTS, DIRECTIONS, Entity, GameState, Pos
from .grid_engine import GridEngine


class RulesEngine:
    """Resolves DungeonGrid actions against a GameState."""

    def __init__(self, grid: GridEngine, rng: random.Random | None = None) -> None:
        self.grid = grid
        self.rng = rng or random.Random()

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
        visible = self.grid.visible_tiles(state, agent_id)
        if ap >= 1:
            actions.append({"type": "message", "target": "party"})
            for ally_id in state.heroes:
                if ally_id != agent_id:
                    actions.append({"type": "message", "target": ally_id})
            for direction, (dx, dy) in DIRECTIONS.items():
                target = (hero.pos[0] + dx, hero.pos[1] + dy)
                if self.grid.is_walkable(state, target):
                    actions.append({"type": "move", "direction": direction, "target": list(target)})
            for door in state.doors.values():
                if door.state == "closed" and door.pos in self.grid.adjacent_positions(hero.pos):
                    if not door.secret or door.discovered:
                        actions.append({"type": "open_door", "target": door.id})
            for pos in [hero.pos, *self.grid.adjacent_positions(hero.pos)]:
                if self.grid.in_bounds(state, pos):
                    actions.append({"type": "inspect_tile", "target": list(pos)})
            for chest in state.chests.values():
                if not chest.opened and self.grid.manhattan(hero.pos, chest.pos) <= 1 and chest.pos in visible:
                    actions.append({"type": "interact", "target": chest.id})
            if state.objective.pos and self.grid.manhattan(hero.pos, state.objective.pos) <= 1 and state.objective.pos in visible:
                actions.append({"type": "interact", "target": state.objective.id})
            if state.objective.carrier == hero.id and hero.pos == state.escape_tile:
                actions.append({"type": "interact", "target": "escape"})
            actions.append({"type": "guard"})
        if ap >= 2:
            for monster in state.monsters.values():
                if monster.alive and monster.pos in visible:
                    if self.grid.manhattan(hero.pos, monster.pos) == 1:
                        actions.append({"type": "attack_melee", "target": monster.id})
                    if self.grid.manhattan(hero.pos, monster.pos) <= 5 and self.grid.line_clear(state, hero.pos, monster.pos):
                        actions.append({"type": "attack_ranged", "target": monster.id})
                        if hero.role == "wizard":
                            actions.append({"type": "cast", "target": monster.id, "payload": {"spell": "spark_lance"}})
            if hero.role == "elf":
                for ally in state.heroes.values():
                    if ally.alive and ally.hp < ally.max_hp and self.grid.manhattan(hero.pos, ally.pos) <= 1:
                        actions.append({"type": "cast", "target": ally.id, "payload": {"spell": "mend_wounds"}})
            for trap in state.traps.values():
                if trap.armed and trap.revealed and self.grid.manhattan(hero.pos, trap.pos) <= 1:
                    actions.append({"type": "disarm", "target": trap.id})
            actions.append({"type": "inspect_room"})
        actions.append({"type": "end_turn"})
        return self._dedupe_actions(actions)

    def _warden_legal_actions(self, state: GameState) -> list[dict[str, Any]]:
        actions = [{"type": "warden_auto"}]
        for monster in state.monsters.values():
            if monster.alive:
                actions.append({"type": "activate_monster", "target": monster.id})
        actions.append({"type": "end_turn"})
        return actions

    def _dedupe_actions(self, actions: list[dict[str, Any]]) -> list[dict[str, Any]]:
        seen: set[str] = set()
        result: list[dict[str, Any]] = []
        for action in actions:
            key = repr(sorted(action.items()))
            if key not in seen:
                seen.add(key)
                result.append(action)
        return result

    def apply_action(self, state: GameState, agent_id: str, action: dict[str, Any]) -> tuple[float, str, dict[str, Any]]:
        """Apply an action. Returns reward, narration, info."""
        if state.done:
            return 0.0, "The quest is already over.", {"done": True}
        active = state.active_agent()
        if agent_id != active:
            state.invalid_actions += 1
            return -1.0, f"Invalid action: {agent_id} is not active; {active} must act.", {"invalid": True}
        action_type = action.get("type")
        legal = self.legal_actions(state, agent_id)
        if not self._action_is_legal(action, legal):
            state.invalid_actions += 1
            return -1.0, f"Invalid action for {agent_id}: {action_type}.", {"invalid": True, "legal_actions": legal}

        if agent_id == "warden":
            if action_type == "warden_auto":
                reward, text = self._warden_auto(state)
                self._end_warden_phase(state)
                return reward, text, {"auto": True}
            if action_type == "activate_monster":
                monster_id = str(action.get("target"))
                reward, text = self._activate_monster(state, monster_id)
                return reward, text, {"monster_id": monster_id}
            if action_type == "end_turn":
                self._end_warden_phase(state)
                return -0.01, "The Warden ends the dungeon phase.", {}

        hero = state.heroes[agent_id]
        known_before = set(state.known_tiles)
        room_ids_before = self._known_room_ids(state, known_before)
        before_damage = sum(h.max_hp - h.hp for h in state.heroes.values())
        reward = -0.01
        narration = ""
        if action_type == "move":
            narration, extra = self._move_hero(state, hero, action)
            reward += extra
        elif action_type == "open_door":
            narration, extra = self._open_door(state, hero, str(action.get("target")))
            reward += extra
        elif action_type in {"attack_melee", "attack_ranged"}:
            narration, extra = self._attack(state, hero, str(action.get("target")), ranged=action_type == "attack_ranged")
            reward += extra
        elif action_type == "cast":
            narration, extra = self._cast(state, hero, str(action.get("target")), action.get("payload", {}))
            reward += extra
        elif action_type == "inspect_tile":
            narration, extra = self._inspect_tile(state, hero, self._pos_from_target(action.get("target"), hero.pos))
            reward += extra
        elif action_type == "inspect_room":
            narration, extra = self._inspect_room(state, hero)
            reward += extra
        elif action_type == "disarm":
            narration, extra = self._disarm(state, hero, str(action.get("target")))
            reward += extra
        elif action_type == "interact":
            narration, extra = self._interact(state, hero, str(action.get("target")))
            reward += extra
        elif action_type == "message":
            narration, extra = self._message(state, hero, action)
            reward += extra
        elif action_type == "guard":
            narration, extra = self._guard(state, hero)
            reward += extra
        elif action_type == "end_turn":
            narration = f"{hero.role} ends their turn."
            state.ap_remaining[hero.id] = 0
            self._advance_hero_turn(state)
        else:
            state.invalid_actions += 1
            return -1.0, f"Unknown action type: {action_type}", {"invalid": True}

        after_damage = sum(h.max_hp - h.hp for h in state.heroes.values())
        if after_damage > before_damage:
            reward -= 0.1 * (after_damage - before_damage)
        self.grid.update_known_tiles(state)
        scout_reward, scout_info = self._scout_reward(
            state,
            known_before=known_before,
            room_ids_before=room_ids_before,
        )
        if scout_reward:
            reward += scout_reward
            state.scout_reward += scout_reward
            narration += (
                f" Scout progress: +{scout_info['new_floor_tiles']} floor tiles"
                f", +{scout_info['new_rooms']} rooms."
            )
        self._check_end_conditions(state)
        if state.done and state.winner == "heroes":
            reward += 1.0
            narration += " The heroes complete the objective and escape."
        elif state.done and state.winner == "dungeon":
            reward -= 1.0
            narration += " The dungeon prevails."
        if action_type != "end_turn" and state.ap_remaining.get(agent_id, 0) <= 0 and not state.done:
            self._advance_hero_turn(state)
        return reward, narration, {"scout_reward": round(scout_reward, 4), **scout_info}

    def _action_is_legal(self, action: dict[str, Any], legal: list[dict[str, Any]]) -> bool:
        atype = action.get("type")
        for candidate in legal:
            if candidate.get("type") != atype:
                continue
            if "direction" in candidate and action.get("direction") != candidate.get("direction"):
                continue
            if "target" in candidate and action.get("target") != candidate.get("target"):
                # Target coordinates may arrive as tuple/list.
                cand_target = candidate.get("target")
                act_target = action.get("target")
                if not (isinstance(cand_target, list) and list(act_target or []) == cand_target):
                    continue
            return True
        return False

    def _cost(self, state: GameState, entity: Entity, action_type: str) -> None:
        state.ap_remaining[entity.id] = max(0, state.ap_remaining.get(entity.id, 0) - ACTION_COSTS.get(action_type, 0))

    def _scout_reward(
        self,
        state: GameState,
        *,
        known_before: set[Pos],
        room_ids_before: set[int],
    ) -> tuple[float, dict[str, Any]]:
        known_after = set(state.known_tiles)
        new_floor_tiles = [
            pos
            for pos in known_after - known_before
            if state.terrain[pos[1]][pos[0]] == "."
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

    def _move_hero(self, state: GameState, hero: Entity, action: dict[str, Any]) -> tuple[str, float]:
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
        state.alert += 1
        return f"{hero.role} opens {door.id}; the passage beyond is now visible.", 0.02

    def _attack(self, state: GameState, attacker: Entity, target_id: str, ranged: bool = False) -> tuple[str, float]:
        target = state.monsters.get(target_id) if attacker.team == "heroes" else state.heroes.get(target_id)
        if target is None or not target.alive:
            return "The attack finds no living target.", -0.2
        self._cost(state, attacker, "attack_ranged" if ranged else "attack_melee")
        attack_dice = max(1, attacker.attack - (1 if ranged and attacker.role != "wizard" else 0))
        if attacker.role == "wizard" and ranged:
            attack_dice = max(2, attacker.focus // 2)
        hits = self._roll_successes(attack_dice)
        guard_dice = target.guard + (1 if "guarded" in target.status else 0)
        blocks = self._roll_successes(guard_dice)
        damage = max(0, hits - blocks)
        if "guarded" in target.status:
            target.status.remove("guarded")
        target.hp -= damage
        if target.team == "heroes":
            state.total_damage_taken += damage
        killed = False
        if target.hp <= 0:
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
                    target.inventory = [item for item in target.inventory if item != state.objective.id]
        mode = "ranged" if ranged else "melee"
        text = f"{attacker.role} makes a {mode} attack on {target.role}: {hits} hits, {blocks} blocks, {damage} damage."
        reward = 0.05 * damage
        if killed:
            text += f" {target.role} is defeated."
            reward += 0.15 if target.team == "dungeon" else -0.3
        return text, reward

    def _cast(self, state: GameState, caster: Entity, target_id: str, payload: dict[str, Any]) -> tuple[str, float]:
        spell = payload.get("spell") or ("mend_wounds" if caster.role == "elf" else "spark_lance")
        if spell == "mend_wounds":
            target = state.heroes.get(target_id)
            if not target or not target.alive:
                return "The healing spell has no valid target.", -0.2
            amount = min(2, target.max_hp - target.hp)
            target.hp += amount
            self._cost(state, caster, "cast")
            return f"{caster.role} mends {target.role}, restoring {amount} hp.", 0.08 * amount
        if spell == "spark_lance":
            target = state.monsters.get(target_id)
            if not target or not target.alive:
                return "The spark lance has no valid target.", -0.2
            self._cost(state, caster, "cast")
            hits = self._roll_successes(max(2, caster.focus // 2))
            blocks = self._roll_successes(target.guard)
            damage = max(0, hits - blocks)
            target.hp -= damage
            killed = target.hp <= 0
            if killed:
                target.hp = 0
                target.alive = False
            text = f"{caster.role} casts spark lance at {target.role}: {damage} damage."
            if killed:
                text += f" {target.role} is defeated."
            return text, 0.08 * damage + (0.15 if killed else 0.0)
        return f"{caster.role} does not know spell {spell}.", -0.2

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
            if state.objective.carrier is None and state.objective.pos is not None:
                if self.grid.manhattan(hero.pos, state.objective.pos) <= 1:
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
        return f"{hero.role} finds nothing useful to interact with.", -0.05

    def _open_chest(self, state: GameState, hero: Entity, contents: str) -> tuple[str, float]:
        if contents in {"coin_cache", "treasure"}:
            state.treasure_collected += 1
            hero.inventory.append("coin_cache")
            return f"{hero.role} opens a chest and collects a small coin cache.", 0.1
        if contents == "healing_draught":
            hero.inventory.append("healing_draught")
            return f"{hero.role} opens a chest and finds a healing draught.", 0.08
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
                )
            return f"{hero.role} opens a chest; a skitterling ambush bursts out.", -0.05
        return f"{hero.role} opens a chest; it is empty.", 0.0

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
            if not monster.alive:
                continue
            # Idle if no hero can currently see the monster and alert is quiet.
            visible_to_party = self.grid.visible_tiles(state, "party")
            if monster.pos not in visible_to_party and state.alert < 2:
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
            target = min(adjacent, key=lambda h: h.hp)
            text, reward = self._monster_attack(state, monster, target)
            return reward, text
        target = min(heroes, key=lambda h: self.grid.manhattan(monster.pos, h.pos))
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

    def _monster_attack(self, state: GameState, monster: Entity, hero: Entity) -> tuple[str, float]:
        hits = self._roll_successes(monster.attack)
        blocks = self._roll_successes(hero.guard + (1 if "guarded" in hero.status else 0))
        if "guarded" in hero.status:
            hero.status.remove("guarded")
        damage = max(0, hits - blocks)
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
        text = f"{monster.role} attacks {hero.role}: {hits} hits, {blocks} blocks, {damage} damage."
        if not hero.alive:
            text += f" {hero.role} is downed."
        return text, -0.1 * damage

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

    def _nearest_free_adjacent(self, state: GameState, pos: Pos) -> Optional[Pos]:
        for candidate in self.grid.adjacent_positions(pos):
            if self.grid.is_walkable(state, candidate):
                return candidate
        return None

    def _pos_from_target(self, target: Any, default: Pos) -> Pos:
        if isinstance(target, (list, tuple)) and len(target) == 2:
            return int(target[0]), int(target[1])
        return default
