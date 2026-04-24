"""Dataclasses and constants used by the three DungeonGrid engines."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Optional

Pos = tuple[int, int]
Team = Literal["heroes", "dungeon"]

DIRECTIONS: dict[str, Pos] = {
    "north": (0, -1),
    "south": (0, 1),
    "west": (-1, 0),
    "east": (1, 0),
}

ACTION_COSTS: dict[str, int] = {
    "move": 1,
    "open_door": 1,
    "attack_melee": 2,
    "attack_ranged": 2,
    "cast": 2,
    "inspect_tile": 1,
    "inspect_room": 2,
    "disarm": 2,
    "interact": 1,
    "use_item": 1,
    "message": 1,
    "guard": 1,
    "end_turn": 0,
    "warden_auto": 0,
    "activate_monster": 0,
}

HERO_ARCHETYPES: dict[str, dict[str, Any]] = {
    "barbarian": {"hp": 9, "speed": 3, "attack": 4, "guard": 2, "focus": 1, "ability": "cleave"},
    "wizard": {"hp": 5, "speed": 3, "attack": 1, "guard": 1, "focus": 5, "ability": "spark_lance"},
    "elf": {"hp": 6, "speed": 4, "attack": 2, "guard": 2, "focus": 3, "ability": "quick_search"},
    "dwarf": {"hp": 7, "speed": 3, "attack": 2, "guard": 3, "focus": 2, "ability": "trapcraft"},
}

MONSTER_TYPES: dict[str, dict[str, Any]] = {
    "skitterling": {"hp": 1, "attack": 1, "guard": 1, "speed": 4, "behavior": "swarm_nearest"},
    "bone_guard": {"hp": 2, "attack": 2, "guard": 2, "speed": 2, "behavior": "hold_room"},
    "gloom_cultist": {"hp": 2, "attack": 1, "guard": 1, "speed": 3, "behavior": "ranged_or_alarm"},
    "crypt_brute": {"hp": 4, "attack": 3, "guard": 2, "speed": 2, "behavior": "protect_objective"},
}

MONSTER_GLYPHS = {
    "G": "skitterling",
    "B": "bone_guard",
    "K": "gloom_cultist",
    "R": "crypt_brute",
}

HERO_GLYPHS = {
    "hero_1": "B",
    "hero_2": "W",
    "hero_3": "E",
    "hero_4": "D",
}

ROLE_GLYPHS = {
    "barbarian": "B",
    "wizard": "W",
    "elf": "E",
    "dwarf": "D",
}

MONSTER_RENDER_GLYPHS = {
    "skitterling": "g",
    "bone_guard": "b",
    "gloom_cultist": "k",
    "crypt_brute": "r",
}


@dataclass(slots=True)
class Entity:
    id: str
    team: Team
    role: str
    hp: int
    max_hp: int
    attack: int
    guard: int
    speed: int
    pos: Pos
    focus: int = 0
    behavior: str = ""
    ability: str = ""
    alive: bool = True
    inventory: list[str] = field(default_factory=list)
    status: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "team": self.team,
            "role": self.role,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "attack": self.attack,
            "guard": self.guard,
            "speed": self.speed,
            "focus": self.focus,
            "behavior": self.behavior,
            "ability": self.ability,
            "pos": list(self.pos),
            "alive": self.alive,
            "inventory": list(self.inventory),
            "status": list(self.status),
        }


@dataclass(slots=True)
class Door:
    id: str
    pos: Pos
    state: Literal["closed", "open"] = "closed"
    secret: bool = False
    discovered: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "pos": list(self.pos),
            "state": self.state,
            "secret": self.secret,
            "discovered": self.discovered,
        }


@dataclass(slots=True)
class Trap:
    id: str
    pos: Pos
    armed: bool = True
    revealed: bool = False
    damage: int = 1

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "pos": list(self.pos),
            "armed": self.armed,
            "revealed": self.revealed,
            "damage": self.damage,
        }


@dataclass(slots=True)
class Chest:
    id: str
    pos: Pos
    opened: bool = False
    contents: str = "coin_cache"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "pos": list(self.pos),
            "opened": self.opened,
            "contents": self.contents,
        }


@dataclass(slots=True)
class Objective:
    id: str
    pos: Optional[Pos]
    carrier: Optional[str] = None
    recovered: bool = False
    fragile: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "pos": list(self.pos) if self.pos else None,
            "carrier": self.carrier,
            "recovered": self.recovered,
            "fragile": self.fragile,
        }


@dataclass(slots=True)
class GameState:
    quest_id: str
    title: str
    difficulty: str
    width: int
    height: int
    terrain: list[list[str]]
    entry: Pos
    escape_tile: Pos
    objective_type: str
    objective: Objective
    heroes: dict[str, Entity]
    monsters: dict[str, Entity]
    doors: dict[str, Door]
    traps: dict[str, Trap]
    chests: dict[str, Chest]
    scripts: dict[str, Any] = field(default_factory=dict)
    round: int = 1
    phase: Literal["hero", "warden", "done"] = "hero"
    turn_index: int = 0
    hero_order: list[str] = field(default_factory=list)
    ap_remaining: dict[str, int] = field(default_factory=dict)
    alert: int = 0
    torch: int = 20
    known_tiles: set[Pos] = field(default_factory=set)
    done: bool = False
    winner: Optional[str] = None
    invalid_actions: int = 0
    violations: int = 0
    total_damage_taken: int = 0
    treasure_collected: int = 0
    scout_reward: float = 0.0
    trace: list[dict[str, Any]] = field(default_factory=list)
    event_log: list[str] = field(default_factory=list)
    party_messages: list[dict[str, Any]] = field(default_factory=list)
    invalid_feedback: list[dict[str, Any]] = field(default_factory=list)

    def active_agent(self) -> str:
        if self.phase == "done":
            return "none"
        if self.phase == "warden":
            return "warden"
        if not self.hero_order:
            return "none"
        self.turn_index = min(self.turn_index, len(self.hero_order) - 1)
        return self.hero_order[self.turn_index]

    def living_heroes(self) -> list[Entity]:
        return [h for h in self.heroes.values() if h.alive]

    def living_monsters(self) -> list[Entity]:
        return [m for m in self.monsters.values() if m.alive]

    def all_entities(self) -> dict[str, Entity]:
        return {**self.heroes, **self.monsters}

    def entity_at(self, pos: Pos, alive_only: bool = True) -> Optional[Entity]:
        for ent in self.all_entities().values():
            if ent.pos == pos and (ent.alive or not alive_only):
                return ent
        return None

    def door_at(self, pos: Pos) -> Optional[Door]:
        return next((door for door in self.doors.values() if door.pos == pos), None)

    def trap_at(self, pos: Pos) -> Optional[Trap]:
        return next((trap for trap in self.traps.values() if trap.pos == pos), None)

    def chest_at(self, pos: Pos) -> Optional[Chest]:
        return next((chest for chest in self.chests.values() if chest.pos == pos), None)

    def to_dict(self, visibility: str = "omniscient") -> dict[str, Any]:
        return {
            "quest_id": self.quest_id,
            "title": self.title,
            "difficulty": self.difficulty,
            "width": self.width,
            "height": self.height,
            "entry": list(self.entry),
            "escape_tile": list(self.escape_tile),
            "objective_type": self.objective_type,
            "objective": self.objective.to_dict(),
            "round": self.round,
            "phase": self.phase,
            "active_agent": self.active_agent(),
            "hero_order": list(self.hero_order),
            "ap_remaining": dict(self.ap_remaining),
            "alert": self.alert,
            "torch": self.torch,
            "done": self.done,
            "winner": self.winner,
            "invalid_actions": self.invalid_actions,
            "violations": self.violations,
            "total_damage_taken": self.total_damage_taken,
            "treasure_collected": self.treasure_collected,
            "scout_reward": round(self.scout_reward, 4),
            "known_tiles": [list(p) for p in sorted(self.known_tiles)],
            "heroes": {k: v.to_dict() for k, v in self.heroes.items()},
            "monsters": {k: v.to_dict() for k, v in self.monsters.items()},
            "doors": {k: v.to_dict() for k, v in self.doors.items()},
            "traps": {k: v.to_dict() for k, v in self.traps.items()},
            "chests": {k: v.to_dict() for k, v in self.chests.items()},
            "event_log_tail": self.event_log[-20:],
            "party_messages_tail": self.party_messages[-20:],
            "invalid_feedback_tail": self.invalid_feedback[-20:],
            "trace_len": len(self.trace),
            "visibility": visibility,
        }
