"""Typed DungeonGrid action vocabulary and tool-schema projection."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any


class DungeonGridActionType(StrEnum):
    MOVE = "move"
    OPEN_DOOR = "open_door"
    ATTACK_MELEE = "attack_melee"
    ATTACK_RANGED = "attack_ranged"
    CAST = "cast"
    INSPECT_TILE = "inspect_tile"
    INSPECT_ROOM = "inspect_room"
    SEARCH_TRAPS = "search_traps"
    SEARCH_SECRETS = "search_secrets"
    SEARCH_TREASURE = "search_treasure"
    SEARCH_FURNITURE = "search_furniture"
    ATTACK_OBJECT = "attack_object"
    DISARM = "disarm"
    INTERACT = "interact"
    USE_ITEM = "use_item"
    EQUIP_ITEM = "equip_item"
    GIVE_ITEM = "give_item"
    MESSAGE = "message"
    GUARD = "guard"
    END_TURN = "end_turn"
    WARDEN_AUTO = "warden_auto"
    ACTIVATE_MONSTER = "activate_monster"
    WARDEN_SPEND_DREAD = "warden_spend_dread"


class DungeonGridDirection(StrEnum):
    NORTH = "north"
    SOUTH = "south"
    WEST = "west"
    EAST = "east"


class DungeonGridTargetKind(StrEnum):
    NONE = "none"
    DIRECTION = "direction"
    ENTITY_ID = "entity_id"
    OBJECT_ID = "object_id"
    ITEM_ID = "item_id"
    TILE = "tile"
    MESSAGE_RECIPIENT = "message_recipient"


@dataclass(frozen=True, slots=True)
class DungeonGridActionContract:
    action_type: DungeonGridActionType
    target_kind: DungeonGridTargetKind
    ap_cost: int
    description: str
    payload_schema: dict[str, Any] | None = None

    def tool_schema(self) -> dict[str, Any]:
        properties: dict[str, Any] = {
            "type": {"type": "string", "const": self.action_type.value},
        }
        required = ["type"]
        if self.target_kind is DungeonGridTargetKind.DIRECTION:
            properties["direction"] = {
                "type": "string",
                "enum": [direction.value for direction in DungeonGridDirection],
            }
            required.append("direction")
        elif self.target_kind is DungeonGridTargetKind.TILE:
            properties["target"] = _tile_target_schema()
            required.append("target")
        elif self.target_kind is not DungeonGridTargetKind.NONE:
            properties["target"] = {"type": "string", "minLength": 1}
            required.append("target")
        if self.payload_schema is not None:
            properties["payload"] = self.payload_schema
            required.append("payload")
        return {
            "type": "object",
            "description": self.description,
            "properties": properties,
            "required": required,
            "additionalProperties": False,
        }


def _tile_target_schema() -> dict[str, Any]:
    return {
        "type": "array",
        "items": {"type": "integer"},
        "minItems": 2,
        "maxItems": 2,
    }


MESSAGE_PAYLOAD_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"text": {"type": "string", "minLength": 1}},
    "required": ["text"],
    "additionalProperties": False,
}

GIVE_ITEM_PAYLOAD_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"item": {"type": "string", "minLength": 1}},
    "required": ["item"],
    "additionalProperties": False,
}

SPELL_PAYLOAD_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {"spell": {"type": "string", "minLength": 1}},
    "required": ["spell"],
    "additionalProperties": False,
}

WARDEN_SPEND_DREAD_PAYLOAD_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "effect": {"type": "string", "minLength": 1},
        "cost": {"type": "integer", "minimum": 0},
    },
    "required": ["effect"],
    "additionalProperties": False,
}

ACTION_CONTRACTS: tuple[DungeonGridActionContract, ...] = (
    DungeonGridActionContract(
        DungeonGridActionType.MOVE,
        DungeonGridTargetKind.DIRECTION,
        1,
        "Move one tile in a cardinal direction.",
    ),
    DungeonGridActionContract(
        DungeonGridActionType.OPEN_DOOR,
        DungeonGridTargetKind.OBJECT_ID,
        1,
        "Open an adjacent known closed door by object id, e.g. door_1.",
    ),
    DungeonGridActionContract(
        DungeonGridActionType.ATTACK_MELEE,
        DungeonGridTargetKind.ENTITY_ID,
        2,
        "Attack an adjacent monster by entity id, e.g. skitterling_1.",
    ),
    DungeonGridActionContract(
        DungeonGridActionType.ATTACK_RANGED,
        DungeonGridTargetKind.ENTITY_ID,
        2,
        "Attack a visible line-of-sight monster by entity id.",
    ),
    DungeonGridActionContract(
        DungeonGridActionType.CAST,
        DungeonGridTargetKind.ENTITY_ID,
        2,
        "Cast a carried spell card. Target is spell-dependent: visible monster id, hero id, self hero id, or cardinal direction for blink_step.",
        payload_schema=SPELL_PAYLOAD_SCHEMA,
    ),
    DungeonGridActionContract(
        DungeonGridActionType.INSPECT_TILE,
        DungeonGridTargetKind.TILE,
        1,
        "Inspect a nearby tile coordinate [x, y]. This is the only action that uses coordinate targets.",
    ),
    DungeonGridActionContract(
        DungeonGridActionType.INSPECT_ROOM,
        DungeonGridTargetKind.NONE,
        2,
        "Broad room search for visible hidden traps or secrets. Prefer search_traps or search_secrets.",
    ),
    DungeonGridActionContract(
        DungeonGridActionType.SEARCH_TRAPS,
        DungeonGridTargetKind.NONE,
        2,
        "Search visible room state for hidden traps only.",
    ),
    DungeonGridActionContract(
        DungeonGridActionType.SEARCH_SECRETS,
        DungeonGridTargetKind.NONE,
        2,
        "Search visible room state for secret doors only.",
    ),
    DungeonGridActionContract(
        DungeonGridActionType.SEARCH_TREASURE,
        DungeonGridTargetKind.OBJECT_ID,
        1,
        "Search an adjacent visible chest or furniture object for treasure by object id.",
    ),
    DungeonGridActionContract(
        DungeonGridActionType.SEARCH_FURNITURE,
        DungeonGridTargetKind.OBJECT_ID,
        1,
        "Search an adjacent visible furniture object by object id.",
    ),
    DungeonGridActionContract(
        DungeonGridActionType.ATTACK_OBJECT,
        DungeonGridTargetKind.OBJECT_ID,
        2,
        "Attack an adjacent visible destructible furniture object by object id.",
    ),
    DungeonGridActionContract(
        DungeonGridActionType.DISARM,
        DungeonGridTargetKind.OBJECT_ID,
        2,
        "Disarm an adjacent revealed trap by trap id.",
    ),
    DungeonGridActionContract(
        DungeonGridActionType.INTERACT,
        DungeonGridTargetKind.OBJECT_ID,
        1,
        "Interact with an adjacent visible object, objective, chest, furniture, or escape by id.",
    ),
    DungeonGridActionContract(
        DungeonGridActionType.USE_ITEM,
        DungeonGridTargetKind.ITEM_ID,
        1,
        "Use an inventory item by item id.",
    ),
    DungeonGridActionContract(
        DungeonGridActionType.EQUIP_ITEM,
        DungeonGridTargetKind.ITEM_ID,
        1,
        "Equip a carried weapon or defensive item by item id.",
    ),
    DungeonGridActionContract(
        DungeonGridActionType.GIVE_ITEM,
        DungeonGridTargetKind.ENTITY_ID,
        1,
        "Give one carried non-objective item to an adjacent living hero. Target is hero id; payload.item is the item id.",
        payload_schema=GIVE_ITEM_PAYLOAD_SCHEMA,
    ),
    DungeonGridActionContract(
        DungeonGridActionType.MESSAGE,
        DungeonGridTargetKind.MESSAGE_RECIPIENT,
        1,
        "Send a coordination message to party or a hero id.",
        payload_schema=MESSAGE_PAYLOAD_SCHEMA,
    ),
    DungeonGridActionContract(
        DungeonGridActionType.GUARD,
        DungeonGridTargetKind.NONE,
        1,
        "Take a guarded stance.",
    ),
    DungeonGridActionContract(
        DungeonGridActionType.END_TURN,
        DungeonGridTargetKind.NONE,
        0,
        "End the active hero turn.",
    ),
    DungeonGridActionContract(
        DungeonGridActionType.WARDEN_AUTO,
        DungeonGridTargetKind.NONE,
        0,
        "Environment-only Warden auto action.",
    ),
    DungeonGridActionContract(
        DungeonGridActionType.ACTIVATE_MONSTER,
        DungeonGridTargetKind.ENTITY_ID,
        0,
        "Environment-only Warden monster activation.",
    ),
    DungeonGridActionContract(
        DungeonGridActionType.WARDEN_SPEND_DREAD,
        DungeonGridTargetKind.ENTITY_ID,
        0,
        "Environment-only Warden dread spend. Target is a hero id; payload.effect names a bounded Warden pressure move.",
        payload_schema=WARDEN_SPEND_DREAD_PAYLOAD_SCHEMA,
    ),
)

ACTION_CONTRACT_BY_TYPE = {contract.action_type.value: contract for contract in ACTION_CONTRACTS}


def action_type_values() -> list[str]:
    return [action_type.value for action_type in DungeonGridActionType]


def direction_values() -> list[str]:
    return [direction.value for direction in DungeonGridDirection]


def action_contract_tool_items_schema(*, include_warden: bool = False) -> dict[str, Any]:
    warden_actions = {
        DungeonGridActionType.WARDEN_AUTO,
        DungeonGridActionType.ACTIVATE_MONSTER,
        DungeonGridActionType.WARDEN_SPEND_DREAD,
    }
    contracts = [
        contract
        for contract in ACTION_CONTRACTS
        if include_warden or contract.action_type not in warden_actions
    ]
    return {"oneOf": [contract.tool_schema() for contract in contracts]}


def warden_action_contract_tool_items_schema() -> dict[str, Any]:
    warden_actions = {
        DungeonGridActionType.WARDEN_AUTO,
        DungeonGridActionType.ACTIVATE_MONSTER,
        DungeonGridActionType.WARDEN_SPEND_DREAD,
        DungeonGridActionType.END_TURN,
    }
    return {
        "oneOf": [
            contract.tool_schema()
            for contract in ACTION_CONTRACTS
            if contract.action_type in warden_actions
        ]
    }


def action_contract_summary() -> str:
    warden_actions = {
        DungeonGridActionType.WARDEN_AUTO,
        DungeonGridActionType.ACTIVATE_MONSTER,
        DungeonGridActionType.WARDEN_SPEND_DREAD,
    }
    return " ".join(
        f"{contract.action_type.value} costs {contract.ap_cost} AP; target={contract.target_kind.value}."
        for contract in ACTION_CONTRACTS
        if contract.action_type not in warden_actions
    )
