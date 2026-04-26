"""Concrete DungeonGrid communication protocol variants."""

from __future__ import annotations

from typing import Any

from .message_protocol import (
    MessageEnvelope,
    MessageProtocol,
    _increment_message_metric,
    _increment_nested_metric,
    initial_message_leader,
)


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
        leader = state.message_metrics.get("current_leader")
        if leader in state.heroes:
            return str(leader)
        return initial_message_leader(state, self.config) or next(iter(state.heroes), "hero_1")

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

    def submit(self, state: Any, actor_id: str, action: dict[str, Any]):
        leader_id = self._leader_id(state)
        result = MessageProtocol.submit(self, state, actor_id, action)
        if result.delivered and actor_id == leader_id:
            self._record_leader_turn(state, leader_id)
            handoff_target = result.envelope.metadata.get("handoff_lead_to") if result.envelope else None
            if handoff_target:
                self._handoff_lead(state, leader_id, str(handoff_target), result.envelope)
        return result

    def validate(
        self, state: Any, actor_id: str, envelope: MessageEnvelope
    ) -> tuple[str, str] | None:
        base_failure = MessageProtocol.validate(self, state, actor_id, envelope)
        if base_failure is not None:
            return base_failure
        leader_id = self._leader_id(state)
        if actor_id != leader_id:
            return (
                "not_current_leader",
                f"{actor_id} cannot send under situational_lead_taking; current leader is {leader_id}.",
            )
        handoff_target = envelope.metadata.get("handoff_lead_to")
        if handoff_target is not None:
            target_id = str(handoff_target)
            if target_id not in state.heroes:
                return "unknown_lead_handoff_target", f"{target_id} is not a known hero."
            if not state.heroes[target_id].alive:
                return "lead_handoff_target_down", f"{target_id} cannot receive lead while down."
        return None

    def public_config(self) -> dict[str, Any]:
        data = MessageProtocol.public_config(self)
        data["leader_policy"] = self.config.get("leader_policy", "first_hero")
        data["leadership"] = "baton_handoff"
        return data

    def _handoff_lead(
        self, state: Any, leader_id: str, target_id: str, envelope: MessageEnvelope
    ) -> None:
        previous = state.message_metrics.get("current_leader")
        state.message_metrics["current_leader"] = target_id
        _increment_message_metric(state, "leader_changes")
        _increment_message_metric(state, "leadership_handoff_count")
        handoff = {
            "kind": "leadership_handoff",
            "round": state.round,
            "from": leader_id,
            "to": target_id,
            "message_id": envelope.message_id,
            "protocol": self.mode,
            "reason": envelope.metadata.get("handoff_reason", ""),
            "previous_leader": previous,
        }
        state.message_metrics.setdefault("leadership_handoffs", []).append(handoff)
        state.message_events.append(handoff)
        state.trace.append(handoff)


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
