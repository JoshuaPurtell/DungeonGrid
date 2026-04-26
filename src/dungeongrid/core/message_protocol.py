"""Communication protocol infrastructure for DungeonGrid hero messages."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


DEFAULT_MESSAGE_PROTOCOL = {
    "mode": "pure_decentralized",
    "max_chars": 240,
    "delivery": "immediate",
    "leader_policy": "first_hero",
}


@dataclass(slots=True)
class MessageEnvelope:
    message_id: str
    round: int
    sender: str
    sender_role: str
    recipient: str
    text: str
    protocol: str
    channel: str = "party"
    delivery_turn: int = 0
    delivered: bool = False
    dropped: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_message(self) -> dict[str, Any]:
        return {
            "message_id": self.message_id,
            "round": self.round,
            "from": self.sender,
            "role": self.sender_role,
            "to": self.recipient,
            "text": self.text,
            "protocol": self.protocol,
            **({"metadata": dict(self.metadata)} if self.metadata else {}),
            **({"channel": self.channel} if self.channel != "party" else {}),
        }

    def to_event(self, kind: str, *, reason: str = "", message: str = "") -> dict[str, Any]:
        event = {
            "kind": kind,
            "message_id": self.message_id,
            "round": self.round,
            "from": self.sender,
            "role": self.sender_role,
            "to": self.recipient,
            "text": self.text,
            "protocol": self.protocol,
        }
        if reason:
            event["reason"] = reason
        if message:
            event["message"] = message
        if self.metadata:
            event["metadata"] = dict(self.metadata)
        return event


@dataclass(slots=True)
class MessageDeliveryResult:
    accepted: bool
    delivered: bool = False
    queued: bool = False
    dropped: bool = False
    reason: str = ""
    message: str = ""
    envelope: MessageEnvelope | None = None


class MessageSubscriber(Protocol):
    def __call__(self, state: Any, event: dict[str, Any]) -> None: ...


class MessageBus:
    """Small message queue/pubsub surface backed by GameState lists."""

    def __init__(self) -> None:
        self._subscribers: dict[str, list[MessageSubscriber]] = {}

    def subscribe(self, event_kind: str, subscriber: MessageSubscriber) -> None:
        self._subscribers.setdefault(event_kind, []).append(subscriber)

    def publish(self, state: Any, event: dict[str, Any]) -> None:
        state.message_events.append(event)
        state.trace.append(event)
        for subscriber in self._subscribers.get(str(event.get("kind")), []):
            subscriber(state, event)

    def record_attempt(self, state: Any, envelope: MessageEnvelope) -> None:
        _increment_message_metric(state, "messages_attempted")
        _increment_nested_metric(state, "messages_by_sender", envelope.sender)
        _increment_nested_metric(state, "messages_by_recipient", envelope.recipient)
        _increment_message_metric(state, "message_chars", len(envelope.text))
        self.publish(state, envelope.to_event("message_submitted"))

    def deliver(self, state: Any, envelope: MessageEnvelope) -> MessageDeliveryResult:
        envelope.delivered = True
        message = envelope.to_message()
        state.party_messages.append(message)
        _increment_message_metric(state, "messages_delivered")
        _increment_social_message_metric(state, "messages_delivered")
        self.publish(state, envelope.to_event("message_delivered"))
        return MessageDeliveryResult(
            accepted=True,
            delivered=True,
            message=f"{envelope.sender_role} to {envelope.recipient}: {envelope.text}",
            envelope=envelope,
        )

    def queue(self, state: Any, envelope: MessageEnvelope) -> MessageDeliveryResult:
        state.message_queue.append(envelope.to_event("message_queued"))
        _increment_message_metric(state, "messages_queued")
        self.publish(state, envelope.to_event("message_queued"))
        return MessageDeliveryResult(
            accepted=True,
            queued=True,
            message=f"{envelope.sender_role}'s message is queued.",
            envelope=envelope,
        )

    def reject(
        self, state: Any, envelope: MessageEnvelope, *, reason: str, message: str
    ) -> MessageDeliveryResult:
        _increment_message_metric(state, "messages_rejected")
        _increment_nested_metric(state, "rejections_by_reason", reason)
        _increment_social_message_metric(state, "messages_rejected")
        self.publish(state, envelope.to_event("message_rejected", reason=reason, message=message))
        return MessageDeliveryResult(
            accepted=False,
            reason=reason,
            message=message,
            envelope=envelope,
        )


class MessageProtocol:
    mode = "pure_decentralized"

    def __init__(self, config: dict[str, Any] | None = None, bus: MessageBus | None = None) -> None:
        self.config = normalize_protocol_config(config)
        self.bus = bus or MessageBus()

    def submit(self, state: Any, actor_id: str, action: dict[str, Any]) -> MessageDeliveryResult:
        envelope = self._envelope(state, actor_id, action)
        envelope.message_id = self._next_message_id(state)
        self.bus.record_attempt(state, envelope)
        failure = self.validate(state, actor_id, envelope)
        if failure is not None:
            reason, message = failure
            return self.bus.reject(state, envelope, reason=reason, message=message)
        return self.bus.deliver(state, envelope)

    def submit_preview(
        self, state: Any, actor_id: str, action: dict[str, Any]
    ) -> MessageDeliveryResult:
        envelope = self._envelope(state, actor_id, action)
        failure = self.validate(state, actor_id, envelope)
        if failure is not None:
            reason, message = failure
            return MessageDeliveryResult(
                accepted=False,
                reason=reason,
                message=message,
                envelope=envelope,
            )
        return MessageDeliveryResult(accepted=True, envelope=envelope)

    def validate(
        self, state: Any, actor_id: str, envelope: MessageEnvelope
    ) -> tuple[str, str] | None:
        if actor_id not in state.heroes:
            return "unknown_sender", f"{actor_id} is not a known hero."
        if envelope.recipient != "party" and envelope.recipient not in state.heroes:
            return "unknown_recipient", f"{envelope.recipient} is not party or a hero id."
        return None

    def visible_messages(self, state: Any, audience_agent_id: str) -> list[dict[str, Any]]:
        if audience_agent_id in {"party", "warden"}:
            return list(state.party_messages)
        return [
            message
            for message in state.party_messages
            if message.get("to") in {"party", audience_agent_id}
            or message.get("from") == audience_agent_id
        ]

    def public_config(self) -> dict[str, Any]:
        return {
            "mode": self.config.get("mode", self.mode),
            "max_chars": self.config.get("max_chars", 240),
            "delivery": self.config.get("delivery", "immediate"),
        }

    def _envelope(self, state: Any, actor_id: str, action: dict[str, Any]) -> MessageEnvelope:
        hero = state.heroes.get(actor_id)
        payload = action.get("payload") if isinstance(action.get("payload"), dict) else {}
        raw_text = payload.get("text") or payload.get("message") or ""
        text = " ".join(str(raw_text).strip().split())
        max_chars = int(self.config.get("max_chars", 240) or 240)
        text = text[: max(1, max_chars)] or "(no message)"
        target = str(action.get("target") or "party")
        return MessageEnvelope(
            message_id="msg_preview",
            round=state.round,
            sender=actor_id,
            sender_role=hero.role if hero else "unknown",
            recipient=target,
            text=text,
            protocol=str(self.config.get("mode") or self.mode),
            channel="party" if target == "party" else "direct",
            delivery_turn=state.round,
            metadata=self._metadata_from_payload(payload),
        )

    def _next_message_id(self, state: Any) -> str:
        index = int(state.message_metrics.get("next_message_index", 1) or 1)
        state.message_metrics["next_message_index"] = index + 1
        return f"msg_{index}"

    def _metadata_from_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        metadata: dict[str, Any] = {}
        for key in ("handoff_lead_to", "handoff_reason", "leadership_intent"):
            if payload.get(key) is not None:
                metadata[key] = payload[key]
        return metadata


def normalize_protocol_config(config: dict[str, Any] | None) -> dict[str, Any]:
    raw = dict(DEFAULT_MESSAGE_PROTOCOL)
    if isinstance(config, dict):
        raw.update(config)
    raw["mode"] = str(raw.get("mode") or "pure_decentralized")
    raw["max_chars"] = int(raw.get("max_chars", 240) or 240)
    raw["delivery"] = str(raw.get("delivery") or "immediate")
    raw["leader_policy"] = str(raw.get("leader_policy") or "first_hero")
    return raw


def protocol_from_state(state: Any) -> MessageProtocol:
    from .message_implementations import message_protocol_from_config

    return message_protocol_from_config(state.communication_protocol)


def configure_message_state(state: Any, config: dict[str, Any] | None = None) -> None:
    state.communication_protocol = normalize_protocol_config(config)
    state.message_queue = []
    state.message_events = []
    state.message_metrics = default_message_metrics(state.heroes)
    state.message_metrics["protocol"] = state.communication_protocol.get("mode", "pure_decentralized")
    state.message_metrics["current_leader"] = initial_message_leader(
        state, state.communication_protocol
    )


def default_message_metrics(heroes: dict[str, Any]) -> dict[str, Any]:
    return {
        "protocol": "pure_decentralized",
        "messages_attempted": 0,
        "messages_delivered": 0,
        "messages_queued": 0,
        "messages_rejected": 0,
        "messages_dropped": 0,
        "message_chars": 0,
        "messages_by_sender": {hero_id: 0 for hero_id in heroes},
        "messages_by_recipient": {"party": 0, **{hero_id: 0 for hero_id in heroes}},
        "next_message_index": 1,
        "leader_changes": 0,
        "leader_turns_by_hero": {hero_id: 0 for hero_id in heroes},
        "current_leader": None,
        "leadership_handoffs": [],
        "leadership_handoff_count": 0,
        "rejections_by_reason": {},
    }


def initial_message_leader(state: Any, config: dict[str, Any]) -> str | None:
    explicit = config.get("leader")
    if explicit in state.heroes:
        return str(explicit)
    if config.get("leader_policy") == "role":
        role = str(config.get("leader_role") or "")
        for hero_id, hero in state.heroes.items():
            if hero.role == role:
                return hero_id
    if state.hero_order:
        return state.hero_order[0]
    return next(iter(state.heroes), None)


def _increment_message_metric(state: Any, metric: str, amount: int = 1) -> None:
    state.message_metrics[metric] = int(state.message_metrics.get(metric, 0) or 0) + amount


def _increment_nested_metric(state: Any, metric: str, key: str, amount: int = 1) -> None:
    values = state.message_metrics.setdefault(metric, {})
    values[key] = int(values.get(key, 0) or 0) + amount


def _increment_social_message_metric(state: Any, metric: str, amount: int = 1) -> None:
    communication = state.social_metrics.setdefault("communication", {})
    communication[metric] = int(communication.get(metric, 0) or 0) + amount
