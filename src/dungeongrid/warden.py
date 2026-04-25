"""Warden policy adapter surfaces for eval and ReAct harnesses."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol

WARDEN_REASONING_FIELDS = (
    "warden_policy",
    "warden_intent",
    "warden_axis_pressure",
    "warden_fairness_check",
)


class WardenPolicy(Protocol):
    """Policy interface for automatic dungeon-side Warden control."""

    def act(self, observation: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(slots=True)
class WardenDecision:
    """One bounded Warden action plus optional transcript reasoning metadata."""

    action: dict[str, Any]
    policy: str = "warden_policy"
    intent: str | None = None
    axis_pressure: str | None = None
    fairness_check: str | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def to_action(self) -> dict[str, Any]:
        action = dict(self.action)
        action.setdefault("warden_policy", self.policy)
        if self.intent:
            action["warden_intent"] = self.intent
        if self.axis_pressure:
            action["warden_axis_pressure"] = self.axis_pressure
        if self.fairness_check:
            action["warden_fairness_check"] = self.fairness_check
        action.update(self.extra)
        return action


class DeterministicWardenPolicy:
    """Network-free Warden policy for reproducible benchmark runs."""

    name = "deterministic_warden"

    def act(self, observation: dict[str, Any]) -> dict[str, Any]:
        legal = observation.get("legal_actions") or [{"type": "end_turn"}]
        for preferred in ("warden_spend_dread", "warden_auto", "activate_monster", "end_turn"):
            for action in legal:
                if action.get("type") == preferred:
                    return WardenDecision(
                        action=dict(action),
                        policy=self.name,
                        intent=_default_intent(observation, preferred),
                        axis_pressure=_marl_axis(observation),
                        fairness_check="bounded legal action selected from Warden candidates",
                    ).to_action()
        return {"type": "end_turn", "warden_policy": self.name}


class WardenReActAdapter:
    """Adapter around a caller-supplied ReAct/model planner.

    The adapter does not call a model itself. The planner receives the Warden
    observation dict and returns either a raw action dict or WardenDecision.
    The adapter keeps the result bounded to the legal Warden action candidates.
    """

    def __init__(
        self,
        planner: Callable[[dict[str, Any]], dict[str, Any] | WardenDecision],
        *,
        name: str = "warden_react",
        fallback: WardenPolicy | None = None,
    ) -> None:
        self.planner = planner
        self.name = name
        self.fallback = fallback or DeterministicWardenPolicy()

    def act(self, observation: dict[str, Any]) -> dict[str, Any]:
        candidate = self.planner(observation)
        decision = candidate if isinstance(candidate, WardenDecision) else WardenDecision(candidate)
        action = decision.to_action()
        action.setdefault("warden_policy", self.name)
        if action_is_legal_warden_choice(action, observation.get("legal_actions") or []):
            return action
        fallback = self.fallback.act(observation)
        fallback["warden_policy"] = f"{self.name}:fallback"
        fallback["warden_intent"] = "planner action was outside bounded Warden candidates"
        fallback["warden_fairness_check"] = "fallback used a legal deterministic Warden action"
        return fallback


def action_is_legal_warden_choice(action: dict[str, Any], legal: list[dict[str, Any]]) -> bool:
    """Return whether an adapter action matches one candidate Warden action."""

    action_type = action.get("type")
    for candidate in legal:
        if candidate.get("type") != action_type:
            continue
        if "target" in candidate and candidate.get("target") != action.get("target"):
            continue
        candidate_payload = candidate.get("payload") or {}
        action_payload = action.get("payload") or {}
        for key, value in candidate_payload.items():
            if action_payload.get(key) != value:
                break
        else:
            return True
    return False


def build_warden_observation(env: Any) -> dict[str, Any]:
    """Build the package-level private/eval Warden observation."""

    state = env._require_state()
    visible_state = env.public_state_json("party")
    metadata = state.scripts.get("metadata", {})
    mechanics = state.scripts.get("mechanics", {})
    marl_contract = mechanics.get("marl_contract", {}) if isinstance(mechanics, dict) else {}
    return {
        "agent_id": "warden",
        "round": state.round,
        "phase": state.phase,
        "active_agent": state.active_agent(),
        "dread": state.dread,
        "alert": state.alert,
        "torch": state.torch,
        "quest_id": state.quest_id,
        "quest_title": state.title,
        "marl_axis": metadata.get("marl_axis") or marl_contract.get("axis"),
        "coordination_type": metadata.get("coordination_type"),
        "marl_contract": marl_contract,
        "warden_policy_contract": mechanics.get("warden_policy", {})
        if isinstance(mechanics, dict)
        else {},
        "visible_hero_progress": {
            "objective": visible_state.get("objective", {}),
            "extracted_heroes": visible_state.get("extracted_heroes", []),
            "hero_treasure": visible_state.get("hero_treasure", {}),
            "social_metrics": visible_state.get("social_metrics", {}),
        },
        "visible_state": visible_state,
        "recent_events": list(state.event_log[-8:]),
        "recent_party_messages": list(state.party_messages[-8:]),
        "legal_actions": env._legal_actions("warden"),
    }


def _marl_axis(observation: dict[str, Any]) -> str | None:
    axis = observation.get("marl_axis")
    return str(axis) if axis else None


def _default_intent(observation: dict[str, Any], action_type: str) -> str:
    axis = _marl_axis(observation) or "the dungeon coordination contract"
    if action_type == "warden_spend_dread":
        return f"spend bounded dread to pressure {axis}"
    if action_type == "warden_auto":
        return f"advance revealed dungeon threats according to {axis}"
    if action_type == "activate_monster":
        return f"activate one revealed threat to test {axis}"
    return "end the Warden turn without extra pressure"
