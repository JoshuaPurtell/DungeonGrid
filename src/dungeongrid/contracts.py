"""OpenEnv ReAct-style tool contracts and compact DungeonGrid rules text."""

from __future__ import annotations

from typing import Any

from .action_contracts import (
    action_contract_summary,
    action_contract_tool_items_schema,
    warden_action_contract_tool_items_schema,
)

RULE_TOPICS = (
    "turn",
    "actions",
    "action_contract",
    "movement",
    "combat",
    "bosses",
    "spells",
    "cards",
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
    "actions": "Actions are JSON objects with a type field. Common types: move {direction}; open_door {target}; attack_melee {target}; attack_ranged {target}; attack_object {target}; cast {target,payload:{spell}}; inspect_tile {target:[x,y]}; search_traps {}; search_secrets {}; search_treasure {target}; search_furniture {target}; disarm {target}; interact {target}; use_item {target}; equip_item {target}; give_item {target,payload:{item}}; message {target,payload:{text}}; guard {}; call_extraction {}; end_turn {}. Coordinates are only valid for inspect_tile. Object/entity actions target ids from visible_objects or visible_entities. Spell targets depend on the spell.",
    "movement": "move costs 1 AP and uses direction north/south/east/west. Only move into adjacent unblocked floor tiles. Closed doors, walls, occupied tiles, and undiscovered secret doors block movement. If a direction was just reported blocked from your current tile, choose a different action.",
    "combat": "attack_melee and attack_ranged cost 2 AP. Melee requires adjacency. Ranged requires visible line of sight and a ranged weapon or spell-like ranged capability. Damage is attack successes minus guard successes. Equipped weapons change attack dice, range, and sometimes damage. Monsters may have readable tactical specials: rat packs punish isolated heroes, sentinels block chokepoints, maulers cleave clustered heroes, cinder mages attack at range, mirror adepts absorb a first damaging hit, and hollow knights can rise once unless countered. Named boss monsters may have phase changes, damage gates, or counterplay hinted by room objects and recent events.",
    "bosses": "Visible boss monsters are marked in observations with a boss name, current phase, public rule summary, and counterplay hint. Bosses may cap incoming damage until a clue, object, furniture, or route flag is resolved; may change phase at HP thresholds; may summon help, raise alert, gain statuses, or unlock dungeon-specific achievements when defeated. Plans stop after boss state changes so the agent can replan.",
    "spells": "Spell cards are carried tactical resources and are consumed when cast unless a card says reusable. cast costs 2 AP with payload.spell. spark_lance targets a visible monster id in line of sight. ward_circle targets self or an adjacent hero and blocks 1 incoming damage once. mend_wounds targets an adjacent wounded hero. blink_step targets a cardinal direction string and moves up to two visible clear tiles. reveal_glyph targets self and reveals nearby traps, secrets, or furniture clues. quiet_step targets self or an adjacent hero and blunts one trap/monster pressure. hush_flame and silence target self and lower alert or cinder/fire pressure.",
    "cards": "Decks include treasure, event, artifact, spell, and dungeon-specific decks. Deck order is deterministic for the dungeon seed. Hidden deck contents are not shown to players, but recent draws and known discard piles are visible. Treasure/artifact/spell decks are usually finite; event decks may reshuffle as recurring pressure. Cards can grant weapons, armor, items, or spell cards; heal or damage; raise or lower alert; reveal traps/secrets/clues; apply statuses; set script flags; spawn or activate monsters; or emit trace text.",
    "classic_dynamic": "Optional classic_dynamic rules add roll-to-move, one major action per hero turn, safe-room search gating, risky treasure draws, bounded Warden dread, and extraction choices. Search actions may be invalid while monsters threaten the room. call_extraction can end with partial success after the objective is secured when the ruleset allows it.",
    "items": "Inventory items are carried by heroes. use_item costs 1 AP. equip_item costs 1 AP and equips a carried weapon or defensive item. Defensive items include shield, chain_mail, leather_jerkin, warding_cloak, iron_helm, and holy_charm. give_item costs 1 AP and transfers one carried non-objective item to an adjacent living hero with payload.item. Healing draught restores HP; lantern lens steadies torch pressure when available. Spell cards are shown separately from equipped gear.",
    "objects": "interact costs 1 AP and is used for adjacent visible objectives and escape. When adjacent to an objective glyph I, interact with the objective id to pick it up. When the objective carrier reaches the escape tile, interact with target escape; on success the episode ends immediately and no later hero or Warden steps run. Prefer search_treasure for adjacent chests or treasure-bearing furniture, and search_furniture for adjacent furniture. attack_object costs 2 AP and targets adjacent visible destructible furniture. Chests may contain gold, weapons, armor, spell cards, useful items, traps, ambushes, or bundles. Searchable furniture may draw cards, grant items or spell cards, raise/lower alert, reveal weaknesses, or trigger dungeon hooks.",
    "traps_locks": "search_traps costs 2 AP and reveals hidden traps in visible room state. search_secrets costs 2 AP and reveals visible secret doors. inspect_tile can still inspect one nearby coordinate. disarm costs 2 AP and works on adjacent revealed armed traps; dwarf has the best chance.",
    "doors_rooms": "open_door costs 1 AP on adjacent known closed doors. Opening a door reveals new room state and stops a queued plan for replanning. Some monsters wake immediately when a room is revealed; others stay dormant until line of sight, alarm/alert, or objective pressure wakes them.",
    "messages": "message costs 1 AP when accepted. Use target party or a hero id from the party roster, with payload.text, to share coordination notes rendered in later observations. The active communication_protocol controls delivery: pure_decentralized allows any hero to speak, no_message rejects messages, master_to_slaves allows only the configured leader, and situational_lead_taking uses baton leadership. In situational_lead_taking, only the current leader can message, and the leader can hand off permission with payload.handoff_lead_to set to another living hero id plus optional payload.handoff_reason.",
    "warden": "The Warden/DM is environment-controlled from the player perspective. In ReAct-Warden evals, a private Warden policy receives revealed/eval Warden state and must choose exactly one bounded Warden action candidate: warden_auto, warden_spend_dread, activate_monster, or end_turn. Invalid or unbounded Warden choices fall back to deterministic Warden control.",
    "scoring": "Objective completion and escape are primary. Reward is non-negative progress credit for survival, exploration, room discovery, treasure, defeated monsters, useful coordination, and unique achievements. Invalid actions, damage, and bad draws remain visible diagnostic metrics and transcript events, but they do not subtract from reward.",
}
RULES["action_contract"] = action_contract_summary()


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
                        "items": action_contract_tool_items_schema(),
                    },
                },
                "required": ["actions"],
                "additionalProperties": False,
            },
        },
    }


def dungeongrid_warden_act_schema() -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": "dungeongrid_warden_act",
            "description": "Submit one bounded Warden action for the private/eval DungeonGrid Warden turn.",
            "parameters": {
                "type": "object",
                "properties": {
                    "intent": {
                        "type": "string",
                        "description": "Brief reason for the Warden pressure move.",
                    },
                    "axis_pressure": {
                        "type": "string",
                        "description": "The MARL/coordination axis this move tests.",
                    },
                    "fairness_check": {
                        "type": "string",
                        "description": "Why this is fair, bounded, and tied to visible/scripted pressure.",
                    },
                    "action": warden_action_contract_tool_items_schema(),
                },
                "required": ["action"],
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
