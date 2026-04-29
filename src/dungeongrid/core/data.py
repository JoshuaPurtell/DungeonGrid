"""Dataclasses and constants used by the three DungeonGrid engines."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

Pos = tuple[int, int]
Team = Literal["heroes", "dungeon"]


@dataclass(slots=True)
class GameModeSpec:
    """Presentation and semantic mode for a DungeonGrid quest.

    ``ruleset`` still controls mechanics such as classic_dynamic movement and
    major actions.  ``GameModeSpec`` controls which side the player party is,
    how roles are named/rendered, and what zero-HP means in narration.
    """

    id: str = "classic"
    party_label: str = "heroes"
    opponent_label: str = "monsters"
    party_collective: str = "party"
    opponent_collective: str = "dungeon"
    party_defeat_status: str = "downed"
    party_defeat_text: str = "{role} is downed."
    opponent_defeat_status: str = "defeated"
    opponent_defeat_text: str = "{role} is defeated."
    role_display_names: dict[str, str] = field(default_factory=dict)
    party_glyphs: dict[str, str] = field(default_factory=dict)
    opponent_glyphs: dict[str, str] = field(default_factory=dict)
    legend: str = (
        "B/W/E/D heroes, g/b/k/r/w/p/n/m/f/y/h monsters, D closed door, / open door, "
        "C chest, A/a/d/v/l/s/$/f furniture, T revealed trap, I objective, E exit."
    )
    quest_brief_template: str = (
        "Quest brief: recover the {item_name} from the dungeon, then bring the carrier "
        "back to the escape tile at {escape_tile}. Explore unopened doors and unrevealed "
        "rooms until the objective glyph I is visible."
    )

    def display_role(self, role: str) -> str:
        return self.role_display_names.get(role, _humanize_role(role))

    def team_label(self, team: Team) -> str:
        return self.party_label if team == "heroes" else self.opponent_label

    def glyph_for(self, *, team: Team, role: str, entity_id: str | None = None) -> str:
        if team == "heroes":
            return self.party_glyphs.get(role, ROLE_GLYPHS.get(role, HERO_GLYPHS.get(entity_id or "", "@")))
        return self.opponent_glyphs.get(role, MONSTER_RENDER_GLYPHS.get(role, "m"))

    def defeat_status_for(self, team: Team) -> str:
        return self.party_defeat_status if team == "heroes" else self.opponent_defeat_status

    def defeat_text_for(self, *, team: Team, role: str) -> str:
        template = self.party_defeat_text if team == "heroes" else self.opponent_defeat_text
        return template.format(role=self.display_role(role), raw_role=role)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "party_label": self.party_label,
            "opponent_label": self.opponent_label,
            "party_collective": self.party_collective,
            "opponent_collective": self.opponent_collective,
            "party_defeat_status": self.party_defeat_status,
            "opponent_defeat_status": self.opponent_defeat_status,
            "role_display_names": dict(self.role_display_names),
            "party_glyphs": dict(self.party_glyphs),
            "opponent_glyphs": dict(self.opponent_glyphs),
            "legend": self.legend,
            "quest_brief_template": self.quest_brief_template,
        }


def _humanize_role(value: str) -> str:
    return str(value).replace("_", " ").strip().title() or "Unknown"


def _deep_merge_dicts(base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in update.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_dicts(dict(merged[key]), value)
        else:
            merged[key] = value
    return merged


def _game_mode_presets() -> dict[str, dict[str, Any]]:
    return {
        "classic": {
            "id": "classic",
            "party_label": "heroes",
            "opponent_label": "monsters",
            "party_collective": "party",
            "opponent_collective": "dungeon",
            "party_defeat_status": "downed",
            "party_defeat_text": "{role} is downed.",
            "opponent_defeat_status": "defeated",
            "opponent_defeat_text": "{role} is defeated.",
            "role_display_names": {
                "barbarian": "Barbarian",
                "wizard": "Wizard",
                "elf": "Elf",
                "dwarf": "Dwarf",
            },
            "party_glyphs": {
                "barbarian": "B",
                "wizard": "W",
                "elf": "E",
                "dwarf": "D",
            },
            "opponent_glyphs": {},
            "legend": (
                "B/W/E/D heroes, g/b/k/r/w/p/n/m/f/y/h monsters, D closed door, / open door, "
                "C chest, A/a/d/v/l/s/$/f furniture, T revealed trap, I objective, E exit."
            ),
            "quest_brief_template": (
                "Quest brief: recover the {item_name} from the dungeon, then bring the carrier "
                "back to the escape tile at {escape_tile}. Explore unopened doors and unrevealed "
                "rooms until the objective glyph I is visible."
            ),
        },
        "goblin": {
            "id": "goblin",
            "party_label": "raiders",
            "opponent_label": "dwarven defenders",
            "party_collective": "goblin crew",
            "opponent_collective": "hold defenders",
            "party_defeat_status": "downed",
            "party_defeat_text": "{role} is downed.",
            "opponent_defeat_status": "knocked_out",
            "opponent_defeat_text": "{role} is knocked out.",
            "role_display_names": {
                "goblin_scout": "Goblin Scout",
                "ogre_bruiser": "Ogre Bruiser",
                "kobold_tinkerer": "Kobold Tinkerer",
                "boggart_trickster": "Boggart Trickster",
                "dwarf_sentry": "Dwarf Sentry",
                "dwarf_shieldbearer": "Dwarf Shieldbearer",
                "dwarf_crossbow": "Dwarf Crossbow",
                "dwarf_runekeeper": "Dwarf Runekeeper",
                "dwarf_warden": "Dwarf Warden",
            },
            "party_glyphs": {
                "goblin_scout": "G",
                "ogre_bruiser": "O",
                "kobold_tinkerer": "K",
                "boggart_trickster": "B",
            },
            "opponent_glyphs": {
                "dwarf_sentry": "d",
                "dwarf_shieldbearer": "s",
                "dwarf_crossbow": "c",
                "dwarf_runekeeper": "r",
                "dwarf_warden": "v",
            },
            "legend": (
                "G/O/K/B raiders, d/s/c/r/v dwarven defenders, D closed door, / open door, "
                "C chest, A/a/d/v/l/s/$/f furniture, T revealed trap, I objective, E exit. "
                "Dwarves reduced to 0 HP are knocked out, not killed."
            ),
            "quest_brief_template": (
                "Quest brief: raid the dwarven hold, recover the {item_name}, and bring the carrier "
                "back to the escape tile at {escape_tile}. Dwarven defenders are knocked out at 0 HP; "
                "avoid lethal language and keep the run playable as an inverted dungeon crawl."
            ),
        },
    }


def classic_game_mode() -> GameModeSpec:
    return game_mode_from_mapping({"id": "classic"})


def game_mode_from_mapping(raw: dict[str, Any] | str | None) -> GameModeSpec:
    if isinstance(raw, str):
        raw_data: dict[str, Any] = {"id": raw}
    elif isinstance(raw, dict):
        raw_data = dict(raw)
    else:
        raw_data = {}
    mode_id = str(raw_data.get("id") or raw_data.get("mode") or "classic")
    presets = _game_mode_presets()
    preset = presets.get(mode_id, presets["classic"])
    merged = _deep_merge_dicts(dict(preset), raw_data)
    glyphs = merged.get("glyphs") if isinstance(merged.get("glyphs"), dict) else {}
    party_glyphs = _deep_merge_dicts(
        dict(merged.get("party_glyphs", {})), dict(glyphs.get("party", {}))
    )
    opponent_glyphs = _deep_merge_dicts(
        dict(merged.get("opponent_glyphs", {})),
        dict(glyphs.get("opponents", glyphs.get("dungeon", {}))),
    )
    return GameModeSpec(
        id=str(merged.get("id", mode_id)),
        party_label=str(merged.get("party_label", "heroes")),
        opponent_label=str(merged.get("opponent_label", "monsters")),
        party_collective=str(merged.get("party_collective", "party")),
        opponent_collective=str(merged.get("opponent_collective", "dungeon")),
        party_defeat_status=str(merged.get("party_defeat_status", "downed")),
        party_defeat_text=str(merged.get("party_defeat_text", "{role} is downed.")),
        opponent_defeat_status=str(merged.get("opponent_defeat_status", "defeated")),
        opponent_defeat_text=str(merged.get("opponent_defeat_text", "{role} is defeated.")),
        role_display_names=dict(merged.get("role_display_names", {})),
        party_glyphs=party_glyphs,
        opponent_glyphs=opponent_glyphs,
        legend=str(merged.get("legend", "")),
        quest_brief_template=str(merged.get("quest_brief_template", "")),
    )


def game_mode_from_quest(data: dict[str, Any]) -> GameModeSpec:
    raw = data.get("game_mode")
    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else {}
    if raw is None:
        raw = metadata.get("game_mode")
    return game_mode_from_mapping(raw)

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
    "call_extraction": 0,
    "warden_auto": 0,
    "activate_monster": 0,
    "warden_spend_dread": 0,
}

MAJOR_ACTION_TYPES: set[str] = {
    "open_door",
    "attack_melee",
    "attack_ranged",
    "cast",
    "inspect_room",
    "search_traps",
    "search_secrets",
    "search_treasure",
    "search_furniture",
    "attack_object",
    "disarm",
    "interact",
}

CLASSIC_DYNAMIC_RULESET: dict[str, Any] = {
    "roll_to_move": {"enabled": True, "dice": [6, 6], "minimum": 2},
    "one_major_action": {
        "enabled": True,
        "open_door_is_major": True,
        "use_item_is_major": False,
        "give_item_is_major": False,
    },
    "safe_room_search": {
        "enabled": True,
        "block_search_actions": [
            "inspect_room",
            "search_traps",
            "search_secrets",
            "search_treasure",
            "search_furniture",
        ],
        "include_visible_corridor_monsters": True,
        "include_dormant_monsters": False,
    },
    "treasure_risk": {"enabled": True, "default_treasure_deck": True},
    "warden_dread": {"enabled": True, "max": 6},
    "extraction": {"enabled": True, "allow_partial": True},
}

DEFAULT_CLASSIC_TREASURE_DECK: list[dict[str, Any]] = [
    {"id": "loose_coin", "name": "Loose Coin", "type": "treasure", "treasure": 1, "reward": 0.06},
    {"id": "old_cache", "name": "Old Cache", "type": "treasure", "treasure": 2, "reward": 0.10},
    {
        "id": "healing_vial",
        "name": "Healing Vial",
        "type": "healing",
        "item": "healing_draught",
        "reward": 0.08,
    },
    {
        "id": "needle_spring",
        "name": "Needle Spring",
        "type": "trap",
        "damage": 1,
        "dread": 1,
        "reward": -0.05,
        "recycle": True,
    },
    {
        "id": "wandering_shape",
        "name": "Wandering Shape",
        "type": "wandering_monster",
        "spawn": {"role": "skitterling", "near": "searching_hero"},
        "dread": 1,
        "reward": -0.08,
        "recycle": True,
    },
]

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
    "rusty_dagger": {
        "name": "Rusty Dagger",
        "melee_dice": 2,
        "ranged_dice": 1,
        "range": 3,
        "roles": ["goblin_scout", "kobold_tinkerer", "boggart_trickster"],
    },
    "sling": {
        "name": "Sling",
        "melee_dice": 1,
        "ranged_dice": 3,
        "range": 5,
        "roles": ["goblin_scout"],
    },
    "ogre_club": {
        "name": "Ogre Club",
        "melee_dice": 5,
        "range": 1,
        "roles": ["ogre_bruiser"],
        "bonus_damage_on_hit": 1,
    },
    "wrench_spear": {
        "name": "Wrench-Spear",
        "melee_dice": 2,
        "range": 1,
        "roles": ["kobold_tinkerer"],
    },
    "boggart_hook": {
        "name": "Boggart Hook",
        "melee_dice": 2,
        "ranged_dice": 2,
        "range": 4,
        "roles": ["boggart_trickster"],
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
    "goblin_scout": {"hp": 4, "speed": 5, "attack": 2, "guard": 1, "focus": 2, "ability": "skulk"},
    "ogre_bruiser": {"hp": 9, "speed": 2, "attack": 5, "guard": 2, "focus": 1, "ability": "slam"},
    "kobold_tinkerer": {"hp": 5, "speed": 4, "attack": 2, "guard": 1, "focus": 4, "ability": "trapcraft"},
    "boggart_trickster": {"hp": 5, "speed": 4, "attack": 2, "guard": 1, "focus": 4, "ability": "trickery"},
}

MONSTER_TYPES: dict[str, dict[str, Any]] = {
    "skitterling": {"hp": 1, "attack": 1, "guard": 1, "speed": 4, "behavior": "swarm_nearest"},
    "bone_guard": {"hp": 2, "attack": 2, "guard": 2, "speed": 2, "behavior": "hold_room"},
    "gloom_cultist": {"hp": 2, "attack": 1, "guard": 1, "speed": 3, "behavior": "ranged_or_alarm"},
    "crypt_brute": {"hp": 4, "attack": 3, "guard": 2, "speed": 2, "behavior": "protect_objective"},
    "lantern_wight": {
        "hp": 3,
        "attack": 2,
        "guard": 2,
        "speed": 3,
        "behavior": "hunt_objective_carrier",
    },
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
    "dwarf_sentry": {"hp": 3, "attack": 2, "guard": 1, "speed": 3, "behavior": "hold_room"},
    "dwarf_shieldbearer": {"hp": 5, "attack": 2, "guard": 3, "speed": 2, "behavior": "hold_chokepoint"},
    "dwarf_crossbow": {
        "hp": 3,
        "attack": 2,
        "guard": 1,
        "speed": 2,
        "behavior": "ranged_alert",
        "attack_range": 6,
        "sight_range": 7,
    },
    "dwarf_runekeeper": {
        "hp": 4,
        "attack": 2,
        "guard": 2,
        "speed": 2,
        "behavior": "ranged_alert",
        "attack_range": 5,
        "sight_range": 7,
    },
    "dwarf_warden": {"hp": 7, "attack": 3, "guard": 3, "speed": 2, "behavior": "protect_objective"},
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
    "Q": "dwarf_sentry",
    "Z": "dwarf_shieldbearer",
    "X": "dwarf_crossbow",
    "U": "dwarf_runekeeper",
    "V": "dwarf_warden",
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
    "goblin_scout": "G",
    "ogre_bruiser": "O",
    "kobold_tinkerer": "K",
    "boggart_trickster": "B",
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
    "dwarf_sentry": "d",
    "dwarf_shieldbearer": "s",
    "dwarf_crossbow": "c",
    "dwarf_runekeeper": "r",
    "dwarf_warden": "v",
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


def default_per_hero_stats(hero: Entity | None = None, *, role: str = "") -> dict[str, Any]:
    hero_role = hero.role if hero is not None else role
    return {
        "role": hero_role,
        "reward": 0.0,
        "actions_submitted": 0,
        "actions_executed": 0,
        "invalid_actions": 0,
        "unused_actions": 0,
        "achievements_unlocked": [],
        "achievement_reward": 0.0,
        "damage_dealt": 0,
        "damage_taken": 0,
        "monsters_defeated": 0,
        "tiles_revealed": 0,
        "rooms_revealed": 0,
        "doors_opened": 0,
        "treasure": 0,
        "items_given": 0,
        "items_received": 0,
        "messages_sent": 0,
        "spell_casts": 0,
        "searches": 0,
        "specialist_actions": 0,
        "extracted": False,
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
    pos: Pos | None
    carrier: str | None = None
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
    mode: GameModeSpec = field(default_factory=classic_game_mode)
    furniture: dict[str, Furniture] = field(default_factory=dict)
    rooms: dict[str, Any] = field(default_factory=dict)
    decks: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    discards: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    hero_loadouts: dict[str, Any] = field(default_factory=dict)
    scripts: dict[str, Any] = field(default_factory=dict)
    ruleset: dict[str, Any] = field(default_factory=dict)
    round: int = 1
    phase: Literal["hero", "warden", "done"] = "hero"
    turn_index: int = 0
    hero_order: list[str] = field(default_factory=list)
    ap_remaining: dict[str, int] = field(default_factory=dict)
    movement_remaining: dict[str, int] = field(default_factory=dict)
    movement_rolls: dict[str, int] = field(default_factory=dict)
    major_action_used: dict[str, bool] = field(default_factory=dict)
    turn_flags: dict[str, Any] = field(default_factory=dict)
    alert: int = 0
    dread: int = 0
    torch: int = 20
    known_tiles: set[Pos] = field(default_factory=set)
    revealed_rooms: set[str] = field(default_factory=set)
    done: bool = False
    winner: str | None = None
    invalid_actions: int = 0
    violations: int = 0
    total_damage_taken: int = 0
    treasure_collected: int = 0
    hero_treasure: dict[str, int] = field(default_factory=dict)
    per_hero_stats: dict[str, dict[str, Any]] = field(default_factory=dict)
    extracted_heroes: set[str] = field(default_factory=set)
    extraction_events: list[dict[str, Any]] = field(default_factory=list)
    termination_reason: str | None = None
    social_metrics: dict[str, Any] = field(default_factory=dict)
    scout_reward: float = 0.0
    achievement_reward: float = 0.0
    achievements_unlocked: set[str] = field(default_factory=set)
    achievement_events: list[dict[str, Any]] = field(default_factory=list)
    quest_achievement_defs: list[Any] = field(default_factory=list)
    trace: list[dict[str, Any]] = field(default_factory=list)
    event_log: list[str] = field(default_factory=list)
    party_messages: list[dict[str, Any]] = field(default_factory=list)
    communication_protocol: dict[str, Any] = field(default_factory=dict)
    message_queue: list[dict[str, Any]] = field(default_factory=list)
    message_events: list[dict[str, Any]] = field(default_factory=list)
    message_metrics: dict[str, Any] = field(default_factory=dict)
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


    def defeat_status(self, entity: Entity) -> str:
        return self.mode.defeat_status_for(entity.team)

    def defeat_message(self, entity: Entity) -> str:
        return self.mode.defeat_text_for(team=entity.team, role=entity.role)

    def mark_defeated(self, entity: Entity) -> str:
        entity.alive = False
        entity.hp = 0
        status = self.defeat_status(entity)
        if status and status not in entity.status:
            entity.status.append(status)
        return status

    def entity_at(self, pos: Pos, alive_only: bool = True) -> Entity | None:
        for ent in self.all_entities().values():
            if ent.pos == pos and (ent.alive or not alive_only):
                return ent
        return None

    def door_at(self, pos: Pos) -> Door | None:
        return next((door for door in self.doors.values() if door.pos == pos), None)

    def trap_at(self, pos: Pos) -> Trap | None:
        return next((trap for trap in self.traps.values() if trap.pos == pos), None)

    def chest_at(self, pos: Pos) -> Chest | None:
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
            "movement_remaining": dict(self.movement_remaining),
            "movement_rolls": dict(self.movement_rolls),
            "major_action_used": dict(self.major_action_used),
            "ruleset": dict(self.ruleset),
            "game_mode": self.mode.to_dict(),
            "alert": self.alert,
            "dread": self.dread,
            "torch": self.torch,
            "done": self.done,
            "winner": self.winner,
            "invalid_actions": self.invalid_actions,
            "violations": self.violations,
            "total_damage_taken": self.total_damage_taken,
            "treasure_collected": self.treasure_collected,
            "hero_treasure": dict(self.hero_treasure),
            "per_hero_stats": {
                hero_id: dict(stats) for hero_id, stats in self.per_hero_stats.items()
            },
            "extracted_heroes": sorted(self.extracted_heroes),
            "extraction_events_tail": self.extraction_events[-20:],
            "termination_reason": self.termination_reason,
            "social_metrics": dict(self.social_metrics),
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
            "communication_protocol": dict(self.communication_protocol),
            "message_queue_tail": self.message_queue[-20:],
            "message_events_tail": self.message_events[-20:],
            "message_metrics": dict(self.message_metrics),
            "invalid_feedback_tail": self.invalid_feedback[-20:],
            "trace_len": len(self.trace),
            "visibility": visibility,
        }
