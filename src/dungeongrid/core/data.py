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
    "search_traps": 2,
    "search_secrets": 2,
    "search_treasure": 1,
    "search_furniture": 1,
    "attack_object": 2,
    "disarm": 2,
    "interact": 1,
    "use_item": 1,
    "equip_item": 1,
    "give_item": 1,
    "message": 1,
    "guard": 1,
    "end_turn": 0,
    "warden_auto": 0,
    "activate_monster": 0,
}

WEAPON_ITEMS: dict[str, dict[str, Any]] = {
    "broad_sword": {
        "name": "Broad Sword",
        "melee_dice": 4,
        "range": 1,
        "roles": ["barbarian", "elf", "dwarf"],
    },
    "cleaver_sword": {
        "name": "Cleaver Sword",
        "melee_dice": 4,
        "range": 1,
        "roles": ["barbarian", "dwarf"],
    },
    "war_cleaver": {
        "name": "War Cleaver",
        "melee_dice": 5,
        "range": 1,
        "roles": ["barbarian"],
    },
    "hand_axe": {
        "name": "Hand Axe",
        "melee_dice": 2,
        "ranged_dice": 2,
        "range": 3,
        "roles": ["barbarian", "elf", "dwarf"],
    },
    "battle_axe": {
        "name": "Battle Axe",
        "melee_dice": 5,
        "range": 1,
        "roles": ["barbarian", "dwarf"],
    },
    "short_bow": {
        "name": "Short Bow",
        "melee_dice": 1,
        "ranged_dice": 3,
        "range": 6,
        "roles": ["elf", "barbarian", "dwarf"],
    },
    "crossbow": {
        "name": "Crossbow",
        "melee_dice": 1,
        "ranged_dice": 4,
        "range": 6,
        "roles": ["barbarian", "elf", "dwarf"],
    },
    "ash_staff": {
        "name": "Ash Staff",
        "melee_dice": 1,
        "ranged_dice": 2,
        "range": 4,
        "roles": ["wizard", "elf"],
        "focus_bonus": 1,
    },
    "rune_staff": {
        "name": "Rune Staff",
        "melee_dice": 1,
        "ranged_dice": 3,
        "range": 5,
        "roles": ["wizard"],
        "focus_bonus": 2,
    },
    "ember_blade": {
        "name": "Ember Blade",
        "melee_dice": 4,
        "range": 1,
        "roles": ["barbarian", "elf", "dwarf"],
        "bonus_damage_on_hit": 1,
    },
}

ARMOR_ITEMS: dict[str, dict[str, Any]] = {
    "shield": {
        "name": "Shield",
        "slot": "offhand",
        "guard": 1,
        "roles": ["barbarian", "elf", "dwarf"],
    },
    "chain_mail": {
        "name": "Chain Mail",
        "slot": "armor",
        "guard": 2,
        "speed": -1,
        "roles": ["barbarian", "dwarf"],
    },
    "leather_jerkin": {
        "name": "Leather Jerkin",
        "slot": "armor",
        "guard": 1,
        "roles": ["barbarian", "elf", "dwarf"],
    },
    "warding_cloak": {
        "name": "Warding Cloak",
        "slot": "cloak",
        "ranged_guard": 1,
        "roles": ["wizard", "elf"],
    },
    "iron_helm": {
        "name": "Iron Helm",
        "slot": "helm",
        "prevents": ["cleave", "lethal"],
        "roles": ["barbarian", "elf", "dwarf"],
    },
    "holy_charm": {
        "name": "Holy Charm",
        "slot": "charm",
        "banishes": ["hollow_knight"],
        "roles": ["barbarian", "wizard", "elf", "dwarf"],
    },
}

SPELL_CARDS: dict[str, dict[str, Any]] = {
    "spark_lance": {
        "name": "Spark Lance",
        "school": "ember",
        "roles": ["wizard"],
        "target": "monster",
        "ap": 2,
        "reusable": False,
        "range": 5,
    },
    "ward_circle": {
        "name": "Ward Circle",
        "school": "ward",
        "roles": ["wizard"],
        "target": "hero",
        "ap": 2,
        "reusable": False,
        "status": "warded",
    },
    "mend_wounds": {
        "name": "Mend Wounds",
        "school": "verdant",
        "roles": ["elf"],
        "target": "hero",
        "ap": 2,
        "reusable": False,
        "heal": 2,
    },
    "blink_step": {
        "name": "Blink Step",
        "school": "moon",
        "roles": ["elf"],
        "target": "direction",
        "ap": 2,
        "reusable": False,
        "range": 2,
    },
    "reveal_glyph": {
        "name": "Reveal Glyph",
        "school": "sight",
        "roles": ["wizard"],
        "target": "self",
        "ap": 2,
        "reusable": False,
    },
    "quiet_step": {
        "name": "Quiet Step",
        "school": "veil",
        "roles": ["elf"],
        "target": "hero",
        "ap": 2,
        "reusable": False,
        "status": "quiet_step",
    },
    "hush_flame": {
        "name": "Hush Flame",
        "school": "ember",
        "roles": ["wizard"],
        "target": "self",
        "ap": 2,
        "reusable": False,
    },
    "silence": {
        "name": "Silence",
        "school": "veil",
        "roles": ["wizard"],
        "target": "self",
        "ap": 2,
        "reusable": False,
    },
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
    "lantern_wight": {"hp": 3, "attack": 2, "guard": 2, "speed": 3, "behavior": "hunt_objective_carrier"},
    "rat_pack": {"hp": 1, "attack": 1, "guard": 0, "speed": 4, "behavior": "isolate_swarm"},
    "iron_sentinel": {"hp": 5, "attack": 2, "guard": 3, "speed": 1, "behavior": "hold_chokepoint"},
    "tusk_mauler": {"hp": 4, "attack": 3, "guard": 2, "speed": 2, "behavior": "cleave_cluster"},
    "cinder_mage": {
        "hp": 2,
        "attack": 2,
        "guard": 1,
        "speed": 2,
        "behavior": "ranged_alert",
        "attack_range": 5,
        "sight_range": 7,
    },
    "mirror_adept": {"hp": 2, "attack": 2, "guard": 1, "speed": 3, "behavior": "decoy_trickster"},
    "hollow_knight": {"hp": 3, "attack": 2, "guard": 2, "speed": 2, "behavior": "revive_guard"},
}

MONSTER_GLYPHS = {
    "G": "skitterling",
    "B": "bone_guard",
    "K": "gloom_cultist",
    "R": "crypt_brute",
    "L": "lantern_wight",
    "P": "rat_pack",
    "N": "iron_sentinel",
    "M": "tusk_mauler",
    "F": "cinder_mage",
    "Y": "mirror_adept",
    "H": "hollow_knight",
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
    "lantern_wight": "w",
    "rat_pack": "p",
    "iron_sentinel": "n",
    "tusk_mauler": "m",
    "cinder_mage": "f",
    "mirror_adept": "y",
    "hollow_knight": "h",
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
    activation: Literal["dormant", "alert", "engaged", "pursuing"] = "dormant"
    room_id: str | None = None
    sight_range: int = 6
    wake_on: str = "room_revealed"
    alive: bool = True
    inventory: list[str] = field(default_factory=list)
    status: list[str] = field(default_factory=list)
    equipment: dict[str, Any] = field(default_factory=dict)

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
            "activation": self.activation,
            "room_id": self.room_id,
            "sight_range": self.sight_range,
            "wake_on": self.wake_on,
            "pos": list(self.pos),
            "alive": self.alive,
            "inventory": list(self.inventory),
            "status": list(self.status),
            "equipment": dict(self.equipment),
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
    contents: Any = "coin_cache"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "pos": list(self.pos),
            "opened": self.opened,
            "contents": self.contents,
        }


@dataclass(slots=True)
class Furniture:
    id: str
    pos: Pos
    category: str
    name: str
    description: str = ""
    deck: str | None = None
    searched: bool = False
    visible: bool = True
    traits: list[str] = field(default_factory=list)
    hp: int = 1
    max_hp: int = 1
    destroyed: bool = False
    destructible: bool = False
    blocks_movement: bool = False
    blocks_los: bool = False
    cover: int = 0
    searched_categories: set[str] = field(default_factory=set)
    search_effects: dict[str, Any] = field(default_factory=dict)
    break_effect: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "pos": list(self.pos),
            "category": self.category,
            "name": self.name,
            "description": self.description,
            "deck": self.deck,
            "searched": self.searched,
            "visible": self.visible,
            "traits": list(self.traits),
            "hp": self.hp,
            "max_hp": self.max_hp,
            "destroyed": self.destroyed,
            "destructible": self.destructible,
            "blocks_movement": self.blocks_movement,
            "blocks_los": self.blocks_los,
            "cover": self.cover,
            "searched_categories": sorted(self.searched_categories),
            "search_effects": dict(self.search_effects),
            "break_effect": self.break_effect,
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
    furniture: dict[str, Furniture] = field(default_factory=dict)
    rooms: dict[str, Any] = field(default_factory=dict)
    decks: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    discards: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    hero_loadouts: dict[str, Any] = field(default_factory=dict)
    scripts: dict[str, Any] = field(default_factory=dict)
    round: int = 1
    phase: Literal["hero", "warden", "done"] = "hero"
    turn_index: int = 0
    hero_order: list[str] = field(default_factory=list)
    ap_remaining: dict[str, int] = field(default_factory=dict)
    alert: int = 0
    torch: int = 20
    known_tiles: set[Pos] = field(default_factory=set)
    revealed_rooms: set[str] = field(default_factory=set)
    done: bool = False
    winner: Optional[str] = None
    invalid_actions: int = 0
    violations: int = 0
    total_damage_taken: int = 0
    treasure_collected: int = 0
    scout_reward: float = 0.0
    achievement_reward: float = 0.0
    achievements_unlocked: set[str] = field(default_factory=set)
    achievement_events: list[dict[str, Any]] = field(default_factory=list)
    quest_achievement_defs: list[Any] = field(default_factory=list)
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
            "terrain": ["".join(row) for row in self.terrain],
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
            "achievement_reward": round(self.achievement_reward, 4),
            "achievements_unlocked": sorted(self.achievements_unlocked),
            "achievement_events_tail": self.achievement_events[-20:],
            "achievement_definitions": [
                definition.to_dict() if hasattr(definition, "to_dict") else dict(definition)
                for definition in self.quest_achievement_defs
            ],
            "known_tiles": [list(p) for p in sorted(self.known_tiles)],
            "revealed_rooms": sorted(self.revealed_rooms),
            "heroes": {k: v.to_dict() for k, v in self.heroes.items()},
            "monsters": {k: v.to_dict() for k, v in self.monsters.items()},
            "doors": {k: v.to_dict() for k, v in self.doors.items()},
            "traps": {k: v.to_dict() for k, v in self.traps.items()},
            "chests": {k: v.to_dict() for k, v in self.chests.items()},
            "furniture": {k: v.to_dict() for k, v in self.furniture.items()},
            "rooms": dict(self.rooms),
            "decks": {k: len(v) for k, v in self.decks.items()},
            "discards": {k: len(v) for k, v in self.discards.items()},
            "hero_loadouts": dict(self.hero_loadouts),
            "event_log_tail": self.event_log[-20:],
            "party_messages_tail": self.party_messages[-20:],
            "invalid_feedback_tail": self.invalid_feedback[-20:],
            "trace_len": len(self.trace),
            "visibility": visibility,
        }
