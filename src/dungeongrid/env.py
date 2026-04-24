"""OpenEnv-style DungeonGrid environment class."""

from __future__ import annotations

import random
from typing import Any

from .core.agent_engine import AgentEngine
from .core.grid_engine import GridEngine
from .core.rules_engine import RulesEngine
from .core.trace import trace_record
from .models import DungeonGridAction, DungeonGridObservation, DungeonGridPlanResult, DungeonGridStep, model_to_dict


class _OpenEnvEnvironment:
    """Tiny local fallback so NanoCoop controls the crawler API shape."""

    pass


class DungeonGridEnvironment(_OpenEnvEnvironment):
    """Text dungeon-crawl environment with an OpenEnv/Gym-like API.

    The public methods intentionally mirror the benchmark interface:
    reset, observe, step, act_plan, render_text, render_ascii, state_json, export_trace.
    """

    def __init__(self, quest_dir: str | None = None) -> None:
        self.grid = GridEngine(quest_dir=quest_dir)
        self.rng = random.Random()
        self.rules = RulesEngine(self.grid, self.rng)
        self.agent_engine = AgentEngine(self.grid, self.rules)
        self.state = None
        self.observation_mode = "mixed"

    def reset(
        self,
        quest_id: str = "lantern_crypt",
        num_heroes: int = 4,
        seed: int | None = None,
        observation_mode: str = "mixed",
    ) -> DungeonGridObservation:
        self.rng.seed(seed)
        self.rules.rng = self.rng
        self.observation_mode = observation_mode
        self.state = self.grid.new_state(quest_id=quest_id, num_heroes=num_heroes, seed=seed)
        return self.observe(self.state.active_agent())

    def observe(self, agent_id: str | None = None) -> DungeonGridObservation:
        state = self._require_state()
        agent_id = agent_id or state.active_agent()
        visible_map = self.grid.render_ascii(state, agent_id=agent_id)
        symbolic = self._symbolic_observation(agent_id, visible_map)
        text = self.render_text(agent_id)
        return DungeonGridObservation(
            agent_id=agent_id,
            active_agent=state.active_agent(),
            round=state.round,
            phase=state.phase,
            text=text,
            visible_map=visible_map,
            symbolic=symbolic,
        )

    def _legal_actions(self, agent_id: str) -> list[dict[str, Any]]:
        """Internal/programmatic legality helper for baselines and adapters."""
        state = self._require_state()
        return self.rules.legal_actions(state, agent_id)

    def step(self, action: DungeonGridAction | dict[str, Any], agent_id: str | None = None) -> DungeonGridStep:
        state = self._require_state()
        action_dict = model_to_dict(action)
        resolved_agent = agent_id or action_dict.pop("agent_id", None) or state.active_agent()
        obs_before = model_to_dict(self.observe(resolved_agent))
        state_before = self.state_json("omniscient")
        reward, narration, info = self.rules.apply_action(state, resolved_agent, action_dict)
        info = {**info, "narration": narration}
        if narration:
            state.event_log.append(narration)
        obs_after = self.observe(state.active_agent() if not state.done else resolved_agent)
        state_after = self.state_json("omniscient")
        state.trace.append(
            trace_record(
                turn_id=len(state.trace),
                round_num=state_before["round"],
                phase=state_before["phase"],
                agent_id=resolved_agent,
                observation=obs_before,
                action={"agent_id": resolved_agent, **action_dict},
                state_before=state_before,
                state_after=state_after,
                narration=narration,
                reward=reward,
                violations=["invalid_action"] if info.get("invalid") else [],
            )
        )
        return DungeonGridStep(observation=obs_after, reward=reward, done=state.done, info=info)

    def act_plan(
        self,
        actions: list[dict[str, Any]],
        intent: str | None = None,
        agent_id: str | None = None,
    ) -> DungeonGridPlanResult:
        state = self._require_state()
        resolved_agent = agent_id or state.active_agent()
        submitted_actions = [dict(action) for action in actions]
        executed_actions: list[dict[str, Any]] = []
        skipped_actions: list[dict[str, Any]] = []
        unused_actions: list[dict[str, Any]] = []
        total_reward = 0.0
        reveal_stopped = False
        reveal_reason: str | None = None

        for index, action in enumerate(submitted_actions):
            if state.done:
                unused_actions.extend(submitted_actions[index:])
                reveal_stopped = True
                reveal_reason = "episode_done"
                break
            if state.active_agent() != resolved_agent:
                unused_actions.extend(submitted_actions[index:])
                reveal_stopped = True
                reveal_reason = "turn_ended"
                break

            before = self._reveal_snapshot()
            step = self.step(action, agent_id=resolved_agent)
            total_reward += step.reward
            if step.info.get("invalid"):
                skipped_actions.append(
                    {
                        "action": dict(action),
                        "reason": step.info.get("invalid_reason", "illegal_action"),
                        "message": (step.info.get("invalid_feedback") or {}).get(
                            "message", step.info.get("narration", "Invalid action.")
                        ),
                    }
                )
                continue

            executed_actions.append(dict(action))
            after = self._reveal_snapshot()
            reveal_reason = self._reveal_reason(action, before, after)
            if reveal_reason:
                unused_actions.extend(submitted_actions[index + 1 :])
                reveal_stopped = True
                break

        observation = self.observe(state.active_agent() if not state.done else resolved_agent)
        result = DungeonGridPlanResult(
            intent=intent,
            submitted_actions=submitted_actions,
            executed_actions=executed_actions,
            skipped_actions=skipped_actions,
            unused_actions=unused_actions,
            reveal_stopped=reveal_stopped,
            reveal_reason=reveal_reason,
            reward=total_reward,
            done=state.done,
            observation=observation,
        )
        state.trace.append(
            {
                "kind": "plan",
                "round": state.round,
                "agent_id": resolved_agent,
                "intent": intent,
                "submitted_actions": submitted_actions,
                "executed_actions": executed_actions,
                "skipped_actions": skipped_actions,
                "unused_actions": unused_actions,
                "reveal_stopped": reveal_stopped,
                "reveal_reason": reveal_reason,
                "reward": round(total_reward, 4),
            }
        )
        return result

    def render_text(self, agent_id: str | None = None) -> str:
        state = self._require_state()
        agent_id = agent_id or state.active_agent()
        active = state.active_agent()
        visible_map = self.grid.render_ascii(state, agent_id=agent_id)
        lines: list[str] = []
        if agent_id == "warden":
            lines.append("You are the Warden.")
        elif agent_id in state.heroes:
            role = state.heroes[agent_id].role
            lines.append(f"You are the {role.title()}.")
        else:
            lines.append(f"Observer: {agent_id}.")
        lines.append(f"Round {state.round}. Phase: {state.phase}. Active agent: {active}.")
        if agent_id in state.heroes:
            hero = state.heroes[agent_id]
            lines.append(
                f"HP {hero.hp}/{hero.max_hp}. AP {state.ap_remaining.get(agent_id, 0)}. "
                f"Position {list(hero.pos)}. Inventory: {hero.inventory or ['empty']}."
            )
        lines.append("\nVisible map:")
        lines.append(visible_map)
        lines.append("\nLegend: B/W/E/D heroes, g/b/k/r monsters, D closed door, / open door, C chest, T revealed trap, I objective, E exit.")
        visible_entities = self.grid.visible_entities(state, agent_id)
        visible_objects = self.grid.visible_objects(state, agent_id)
        if visible_entities:
            lines.append("\nVisible entities:")
            for ent in visible_entities:
                if ent["id"] != agent_id:
                    lines.append(f"- {ent['id']} ({ent['role']}) at {ent['pos']} hp {ent['hp']}/{ent['max_hp']}")
        if visible_objects:
            lines.append("\nVisible objects:")
            for obj in visible_objects:
                label = obj.get("id", obj.get("type"))
                lines.append(f"- {obj['type']} {label} at {obj.get('pos')}")
        carrier = state.objective.carrier or "not carried"
        lines.append(f"\nObjective: recover {state.objective.id} and reach {list(state.escape_tile)}. Carrier: {carrier}.")
        if state.event_log:
            lines.append("\nRecent events:")
            for event in state.event_log[-3:]:
                lines.append(f"- {event}")
        if state.party_messages:
            lines.append("\nRecent party messages:")
            for message in state.party_messages[-5:]:
                lines.append(
                    f"- {message.get('from')} -> {message.get('to')}: {message.get('text')}"
                )
        if state.invalid_feedback:
            lines.append("\nRecent invalid action feedback:")
            for feedback in state.invalid_feedback[-3:]:
                lines.append(
                    f"- {feedback.get('agent_id')}: {feedback.get('reason')} - {feedback.get('message')}"
                )
        lines.append(
            "\nSubmit structured JSON actions with dungeongrid_act. "
            "Use dungeongrid_rules for action schemas and rule details."
        )
        return "\n".join(lines)

    def render_ascii(self, agent_id: str | None = None) -> str:
        return self.grid.render_ascii(self._require_state(), agent_id=agent_id)

    def state_json(self, visibility: str = "omniscient") -> dict[str, Any]:
        state = self._require_state()
        if visibility == "omniscient":
            return state.to_dict(visibility=visibility)
        # Party-known state keeps hidden trap/chest contents redacted.
        data = state.to_dict(visibility=visibility)
        if visibility != "warden":
            for trap in data["traps"].values():
                if not trap["revealed"]:
                    trap.pop("pos", None)
            for chest in data["chests"].values():
                chest.pop("contents", None)
        return data

    def export_trace(self) -> dict[str, Any]:
        state = self._require_state()
        return {"quest_id": state.quest_id, "title": state.title, "trace": list(state.trace), "metrics": self.agent_engine.metrics(state)}

    def _symbolic_observation(self, agent_id: str, visible_map: str) -> dict[str, Any]:
        state = self._require_state()
        visible_tiles = self.grid.visible_tiles(state, agent_id)
        visible_entities = self.grid.visible_entities(state, agent_id)
        visible_objects = self.grid.visible_objects(state, agent_id)
        self_data = None
        if agent_id in state.all_entities():
            self_data = state.all_entities()[agent_id].to_dict()
        return {
            "agent_id": agent_id,
            "round": state.round,
            "phase": state.phase,
            "active_agent": state.active_agent(),
            "ap_remaining": state.ap_remaining.get(agent_id, 0),
            "self": self_data,
            "visible_tiles": [list(p) for p in sorted(visible_tiles)],
            "visible_entities": visible_entities,
            "visible_objects": visible_objects,
            "visible_map": visible_map,
            "objective": state.objective.to_dict(),
            "known_objective": f"recover_{state.objective.id}_and_escape",
            "party_messages": list(state.party_messages[-10:]),
            "invalid_feedback": list(state.invalid_feedback[-5:]),
            "alert": state.alert if agent_id == "warden" else None,
            "torch": state.torch,
        }

    def _reveal_snapshot(self) -> dict[str, Any]:
        state = self._require_state()
        return {
            "active_agent": state.active_agent(),
            "phase": state.phase,
            "done": state.done,
            "doors": {
                door_id: {"state": door.state, "discovered": door.discovered}
                for door_id, door in state.doors.items()
            },
            "traps": {
                trap_id: {"revealed": trap.revealed, "armed": trap.armed}
                for trap_id, trap in state.traps.items()
            },
            "chests": {chest_id: {"opened": chest.opened} for chest_id, chest in state.chests.items()},
            "objective": state.objective.to_dict(),
        }

    def _reveal_reason(
        self,
        action: dict[str, Any],
        before: dict[str, Any],
        after: dict[str, Any],
    ) -> str | None:
        if after["done"] and not before["done"]:
            return "episode_done"
        for door_id, before_door in before["doors"].items():
            after_door = after["doors"].get(door_id, {})
            if before_door.get("state") == "closed" and after_door.get("state") == "open":
                return "door_opened"
            if not before_door.get("discovered") and after_door.get("discovered"):
                return "secret_revealed"
        for trap_id, before_trap in before["traps"].items():
            after_trap = after["traps"].get(trap_id, {})
            if not before_trap.get("revealed") and after_trap.get("revealed"):
                return "trap_revealed"
        for chest_id, before_chest in before["chests"].items():
            after_chest = after["chests"].get(chest_id, {})
            if not before_chest.get("opened") and after_chest.get("opened"):
                return "chest_revealed"
        if before["objective"] != after["objective"]:
            return "objective_changed"
        if before["active_agent"] != after["active_agent"] or before["phase"] != after["phase"]:
            return "turn_ended"
        return None

    def _require_state(self):
        if self.state is None:
            self.reset()
        return self.state


# Backwards-compatible alias matching the handoff language.
DungeonGridEnv = DungeonGridEnvironment
