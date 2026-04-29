"""AgentEngine: baseline policies, Warden script policy, rollouts, metrics."""

from __future__ import annotations

import random
from typing import Any, Protocol

from .data import DIRECTIONS, GameState
from .grid_engine import GridEngine
from .rules_engine import RulesEngine


class Policy(Protocol):
    def act(self, observation: dict[str, Any]) -> dict[str, Any]: ...


class RandomLegalPolicy:
    """Uniform random baseline over provided legal actions."""

    def __init__(self, seed: int | None = None) -> None:
        self.rng = random.Random(seed)

    def act(self, observation: dict[str, Any]) -> dict[str, Any]:
        legal = observation.get("legal_actions") or [{"type": "end_turn"}]
        return self.rng.choice(legal)


class GreedyHeroPolicy:
    """Simple baseline: attack, pick objective, escape, open doors, move to frontier."""

    def __init__(self, seed: int | None = None) -> None:
        self.rng = random.Random(seed)

    def act(self, observation: dict[str, Any]) -> dict[str, Any]:
        legal = observation.get("legal_actions") or [{"type": "end_turn"}]
        for preferred in ("attack_melee", "cast", "attack_ranged"):
            for action in legal:
                if action.get("type") == preferred:
                    return action
        for action in legal:
            if action.get("type") == "interact" and action.get("target") in {
                observation.get("symbolic", {}).get("objective", {}).get("id"),
                "escape",
            }:
                return action
        for action in legal:
            if action.get("type") == "open_door":
                return action
        for action in legal:
            if action.get("type") == "interact":
                return action
        for action in legal:
            if action.get("type") == "inspect_room":
                return action
        moves = [a for a in legal if a.get("type") == "move"]
        if moves:
            return self.rng.choice(moves)
        return {"type": "end_turn"}


class AchievementScoutPolicy(GreedyHeroPolicy):
    """Baseline that prioritizes visible progress achievements over rushing combat."""

    def act(self, observation: dict[str, Any]) -> dict[str, Any]:
        legal = observation.get("legal_actions") or [{"type": "end_turn"}]
        if any(action.get("type") == "message" for action in legal):
            roster = observation.get("symbolic", {}).get("party_roster") or []
            unlocked = set(observation.get("symbolic", {}).get("achievements_unlocked", []))
            if len(roster) >= 2 and "coordination.message_sent" not in unlocked:
                return {
                    "type": "message",
                    "target": "party",
                    "payload": {
                        "text": "I am scouting for doors, furniture, traps, and objective progress."
                    },
                }
        for action in legal:
            if action.get("type") == "interact":
                target = str(action.get("target"))
                if target.startswith(
                    (
                        "sarcophagus",
                        "oil_",
                        "weapon_",
                        "bell_",
                        "rite_",
                        "supply_",
                        "spice_",
                        "ledger_",
                        "ash_",
                        "cinder_",
                        "exit_",
                        "guard_",
                        "north_",
                        "west_",
                        "south_",
                    )
                ):
                    return action
        for action in legal:
            if action.get("type") in {"open_door", "inspect_room", "inspect_tile", "disarm"}:
                return action
        return super().act(observation)


class ScriptedWardenPolicy:
    """Default Warden: activate all alert/revealed monsters through the rules engine."""

    def act(self, observation: dict[str, Any]) -> dict[str, Any]:
        for action in observation.get("legal_actions", []):
            if action.get("type") == "warden_auto":
                return action
        return {"type": "end_turn"}


class AgentEngine:
    """Utility wrapper for running policies through GridEngine + RulesEngine."""

    def __init__(self, grid: GridEngine, rules: RulesEngine, seed: int | None = None) -> None:
        self.grid = grid
        self.rules = rules
        self.rng = random.Random(seed)

    def scripted_warden_action(self, state: GameState) -> dict[str, Any]:
        legal = self.rules.legal_actions(state, "warden")
        for action in legal:
            if action["type"] == "warden_auto":
                return action
        return {"type": "end_turn"}

    def metrics(self, state: GameState) -> dict[str, Any]:
        floor_tiles = sum(1 for row in state.terrain for cell in row if cell == ".")
        explored = len([p for p in state.known_tiles if state.terrain[p[1]][p[0]] == "."])
        rooms = self._room_regions(state)
        rooms_explored = sum(1 for room in rooms if room & state.known_tiles)
        living = len(state.living_heroes())
        quest_achievements = [
            achievement_id
            for achievement_id in state.achievements_unlocked
            if achievement_id.startswith(f"{state.quest_id}.")
        ]
        global_achievements = [
            achievement_id
            for achievement_id in state.achievements_unlocked
            if not achievement_id.startswith(f"{state.quest_id}.")
        ]
        return {
            "success": state.done and state.winner == "heroes",
            "game_mode": state.mode.id,
            "party_label": state.mode.party_label,
            "opponent_label": state.mode.opponent_label,
            "winner": state.winner,
            "rounds": state.round,
            "survival": living / max(1, len(state.heroes)),
            "heroes_alive": living,
            "damage": state.total_damage_taken,
            "treasure": state.treasure_collected,
            "hero_treasure": dict(state.hero_treasure),
            "per_hero_stats": self._per_hero_stats(state),
            "dread": state.dread,
            "extracted_heroes": len(state.extracted_heroes),
            "extraction_rate": len(state.extracted_heroes) / max(1, len(state.heroes)),
            "termination_reason": state.termination_reason,
            "social_metrics": dict(state.social_metrics),
            "exploration": explored / max(1, floor_tiles),
            "explored_tiles": explored,
            "floor_tiles": floor_tiles,
            "rooms_explored": rooms_explored,
            "room_count": len(rooms),
            "room_exploration": rooms_explored / max(1, len(rooms)),
            "scout_reward": round(state.scout_reward, 4),
            "achievement_reward": round(state.achievement_reward, 4),
            "achievements_unlocked": sorted(state.achievements_unlocked),
            "achievement_count": len(state.achievements_unlocked),
            "quest_achievement_count": len(quest_achievements),
            "global_achievement_count": len(global_achievements),
            "rule_violations": state.violations,
            "invalid_actions": state.invalid_actions,
            "monsters_defeated": len([m for m in state.monsters.values() if not m.alive]),
            "opponents_defeated": len([m for m in state.monsters.values() if not m.alive]),
            "opponents_knocked_out": len(
                [m for m in state.monsters.values() if "knocked_out" in m.status]
            ),
        }

    def _per_hero_stats(self, state: GameState) -> dict[str, dict[str, Any]]:
        stats_by_hero: dict[str, dict[str, Any]] = {}
        for hero_id, hero in state.heroes.items():
            raw = dict(state.per_hero_stats.get(hero_id, {}))
            raw.setdefault("role", hero.role)
            raw["reward"] = round(float(raw.get("reward", 0.0) or 0.0), 4)
            raw["achievement_reward"] = round(float(raw.get("achievement_reward", 0.0) or 0.0), 4)
            raw["treasure"] = int(state.hero_treasure.get(hero_id, raw.get("treasure", 0)))
            raw["extracted"] = hero_id in state.extracted_heroes
            raw["alive"] = hero.alive
            raw["hp"] = hero.hp
            raw["max_hp"] = hero.max_hp
            raw["achievement_count"] = len(raw.get("achievements_unlocked", []) or [])
            stats_by_hero[hero_id] = raw
        return stats_by_hero

    def _room_regions(self, state: GameState) -> list[set[tuple[int, int]]]:
        blocked_doors = {door.pos for door in state.doors.values()}
        floor = {
            (x, y)
            for y, row in enumerate(state.terrain)
            for x, cell in enumerate(row)
            if cell == "." and (x, y) not in blocked_doors
        }
        regions: list[set[tuple[int, int]]] = []
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

    def move_toward(
        self, state: GameState, actor_id: str, target: tuple[int, int]
    ) -> dict[str, Any]:
        actor = state.all_entities()[actor_id]
        best = None
        best_dist = 10**9
        for direction, (dx, dy) in DIRECTIONS.items():
            pos = (actor.pos[0] + dx, actor.pos[1] + dy)
            if not self.grid.is_walkable(state, pos):
                continue
            dist = self.grid.manhattan(pos, target)
            if dist < best_dist:
                best = {"type": "move", "direction": direction}
                best_dist = dist
        return best or {"type": "end_turn"}
