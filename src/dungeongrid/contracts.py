"""OpenEnv ReAct-style tool contracts and compact DungeonGrid rules text."""

from __future__ import annotations

from typing import Any

RULE_TOPICS = (
    "turn",
    "actions",
    "movement",
    "combat",
    "spells",
    "items",
    "objects",
    "traps_locks",
    "doors_rooms",
    "messages",
    "warden",
    "scoring",
)

RULES: dict[str, str] = {
    "turn": "Heroes act one at a time with 3 AP. Submit a queued JSON action plan for only the active hero. Execution stops at AP/turn end, episode end, or a reveal boundary.",
    "actions": "Actions are JSON objects with a type field. Common types: move {direction}; open_door {target}; attack_melee {target}; attack_ranged {target}; cast {target,payload:{spell}}; inspect_tile {target:[x,y]}; inspect_room {}; disarm {target}; interact {target}; message {target,payload:{text}}; guard {}; end_turn {}.",
    "movement": "move costs 1 AP and uses direction north/south/east/west. Closed doors, walls, occupied tiles, and undiscovered secret doors block movement.",
    "combat": "attack_melee and attack_ranged cost 2 AP. Melee requires adjacency. Ranged requires visible line of sight. Damage is attack successes minus guard successes.",
    "spells": "Wizard can use spark_lance against visible monsters. Elf can use mend_wounds on adjacent wounded heroes. Cast actions cost 2 AP.",
    "items": "Inventory items are carried by heroes. Current alpha item effects are limited; richer item/card systems are planned.",
    "objects": "interact costs 1 AP and is used for adjacent visible chests, objectives, and escape when carrying the objective at the exit.",
    "traps_locks": "inspect_tile and inspect_room can reveal hidden traps or secret doors. disarm costs 2 AP and works on adjacent revealed armed traps; dwarf has the best chance.",
    "doors_rooms": "open_door costs 1 AP on adjacent known closed doors. Opening a door reveals new room state and stops a queued plan for replanning.",
    "messages": "message costs 1 AP. Use target party or a hero id and payload.text to share durable coordination notes rendered in later observations.",
    "warden": "The Warden/DM is always environment-controlled. Player policies never control Warden actions.",
    "scoring": "Objective completion and escape are primary. Secondary reward credits survival, exploration, room discovery, treasure, defeated monsters, and penalizes invalid actions and damage.",
}


def dungeongrid_act_schema() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "dungeongrid_act",
            "description": "Submit the active DungeonGrid hero's queued OpenEnv ReAct action plan.",
            "parameters": {
                "type": "object",
                "properties": {
                    "intent": {
                        "type": "string",
                        "description": "Brief natural-language plan summary for transcript review.",
                    },
                    "actions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "type": {"type": "string"},
                                "direction": {"type": "string"},
                                "target": {},
                                "payload": {"type": "object"},
                            },
                            "required": ["type"],
                            "additionalProperties": True,
                        },
                    },
                },
                "required": ["actions"],
                "additionalProperties": False,
            },
        },
    }


def dungeongrid_rules_schema() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "dungeongrid_rules",
            "description": "Query compact DungeonGrid rules and action schema details.",
            "parameters": {
                "type": "object",
                "properties": {
                    "topic": {
                        "type": "string",
                        "enum": list(RULE_TOPICS),
                    }
                },
                "required": ["topic"],
                "additionalProperties": False,
            },
        },
    }


def dungeongrid_rules(topic: str = "actions") -> str:
    return RULES.get(topic, RULES["actions"])
