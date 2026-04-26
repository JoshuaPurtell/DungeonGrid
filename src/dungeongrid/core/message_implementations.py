"""Concrete DungeonGrid communication protocol variants."""

from __future__ import annotations

from typing import Any

from .message_protocol import MessageEnvelope, MessageProtocol, _increment_nested_metric


class PureDecentralizedProtocol(MessageProtocol):
    mode = "pure_decentralized"


class NoMessageProtocol(MessageProtocol):
    mode = "no_message"

    def validate(
        self, state: Any, actor_id: str, envelope: MessageEnvelope
    ) -> tuple[str, str] | None:
        return (
            "communication_disabled",
            "The active communication protocol disables message actions.",
        )


class MasterToSlavesProtocol(MessageProtocol):
    mode = "master_to_slaves"

    def submit(self, state: Any, actor_id: str, action: dict[str, Any]):
        leader_id = self._leader_id(state)
        result = super().submit(state, actor_id, action)
        if result.delivered and actor_id == leader_id:
            self._record_leader_turn(state, leader_id)
        return result

    def validate(
        self, state: Any, actor_id: str, envelope: MessageEnvelope
    ) -> tuple[str, str] | None:
        base_failure = super().validate(state, actor_id, envelope)
        if base_failure is not None:
            return base_failure
        leader_id = self._leader_id(state)
        if actor_id == leader_id:
            return None
        if bool(self.config.get("followers_can_reply", False)) and envelope.recipient == leader_id:
            return None
        return (
            "not_designated_leader",
            f"{actor_id} cannot send under {self.mode}; current leader is {leader_id}.",
        )

    def public_config(self) -> dict[str, Any]:
        data = super().public_config()
        data["leader_policy"] = self.config.get("leader_policy", "first_hero")
        data["leader"] = self.config.get("leader")
        data["followers_can_reply"] = bool(self.config.get("followers_can_reply", False))
        return data

    def _leader_id(self, state: Any) -> str:
        explicit = self.config.get("leader")
        if explicit in state.heroes:
            return str(explicit)
        if self.config.get("leader_policy") == "role":
            role = str(self.config.get("leader_role") or "")
            for hero_id, hero in state.heroes.items():
                if hero.role == role:
                    return hero_id
        if state.hero_order:
            return state.hero_order[0]
        return next(iter(state.heroes), "hero_1")

    def _record_leader_turn(self, state: Any, leader_id: str) -> None:
        previous = state.message_metrics.get("current_leader")
        if previous != leader_id:
            state.message_metrics["current_leader"] = leader_id
            state.message_metrics["leader_changes"] = (
                int(state.message_metrics.get("leader_changes", 0) or 0) + 1
            )
        _increment_nested_metric(state, "leader_turns_by_hero", leader_id)


class SituationalLeadTakingProtocol(MasterToSlavesProtocol):
    mode = "situational_lead_taking"

    def _leader_id(self, state: Any) -> str:
        carrier = state.objective.carrier
        if carrier in state.heroes and state.heroes[carrier].alive:
            return carrier
        revealer = state.scripts.get("last_room_revealer")
        revealer_round = int(state.scripts.get("last_room_revealer_round", -999) or -999)
        revealer_duration = int(self.config.get("room_revealer_rounds", 1) or 1)
        if (
            revealer in state.heroes
            and state.heroes[revealer].alive
            and state.round - revealer_round <= revealer_duration
        ):
            return str(revealer)
        specialist = self._visible_specialist_leader(state)
        if specialist:
            return specialist
        wounded = self._wounded_leader(state)
        if wounded:
            return wounded
        if state.hero_order:
            return state.hero_order[(max(1, state.round) - 1) % len(state.hero_order)]
        return next(iter(state.heroes), "hero_1")

    def public_config(self) -> dict[str, Any]:
        data = MessageProtocol.public_config(self)
        data["leader_policy"] = "objective_carrier_then_room_revealer_then_specialist_then_wounded_then_round_robin"
        return data

    def _visible_specialist_leader(self, state: Any) -> str | None:
        required = state.scripts.get("role_requirements", {})
        roles = required.get("required_roles") if isinstance(required, dict) else None
        if not isinstance(roles, list):
            return None
        for role in roles:
            for hero_id, hero in state.heroes.items():
                if hero.alive and hero.role == str(role):
                    return hero_id
        return None

    def _wounded_leader(self, state: Any) -> str | None:
        wounded = [
            hero
            for hero in state.heroes.values()
            if hero.alive and hero.hp <= max(1, hero.max_hp // 2)
        ]
        if not wounded:
            return None
        return min(wounded, key=lambda hero: hero.hp).id


def message_protocol_from_config(config: dict[str, Any] | None) -> MessageProtocol:
    mode = str((config or {}).get("mode") or "pure_decentralized")
    registry = {
        "pure_decentralized": PureDecentralizedProtocol,
        "free_text": PureDecentralizedProtocol,
        "no_message": NoMessageProtocol,
        "master_to_slaves": MasterToSlavesProtocol,
        "situational_lead_taking": SituationalLeadTakingProtocol,
    }
    cls = registry.get(mode, PureDecentralizedProtocol)
    return cls(config)
