"""OpenEnv-style DungeonGrid environment class."""

from __future__ import annotations

import base64
import copy
import pickle
import random
from pathlib import Path
from typing import Any

from .achievements import AchievementEngine
from .core.agent_engine import AgentEngine
from .core.data import DIRECTIONS, default_per_hero_stats
from .core.grid_engine import GridEngine
from .core.rules_engine import RulesEngine
from .core.trace import trace_record
from .hooks import HookContext, HookEngine
from .models import (
    DungeonGridAction,
    DungeonGridObservation,
    DungeonGridPlanResult,
    DungeonGridStep,
    model_to_dict,
)
from .warden import WARDEN_REASONING_FIELDS, build_warden_observation

CHECKPOINT_VERSION = "dungeongrid.environment_checkpoint.v1"


class _OpenEnvEnvironment:
    """Minimal base class for the local OpenEnv-style API."""

    pass


class DungeonGridEnvironment(_OpenEnvEnvironment):
    """Text dungeon-crawl environment with an OpenEnv/Gym-like API.

    The public methods intentionally mirror the benchmark interface:
    reset, observe, step, act_plan, render_text, render_ascii, state_json, export_trace.
    """

    def __init__(self, quest_dir: str | None = None) -> None:
        self.quest_dir = str(quest_dir) if quest_dir is not None else None
        self.grid = GridEngine(quest_dir=quest_dir)
        self.hooks = HookEngine(dungeon_dir=quest_dir)
        self.rng = random.Random()
        self.rules = RulesEngine(self.grid, self.rng)
        self.rules.hooks = self.hooks
        self.agent_engine = AgentEngine(self.grid, self.rules)
        self.achievements = AchievementEngine()
        self.state = None
        self.observation_mode = "mixed"

    def reset(
        self,
        quest_id: str = "lantern_crypt",
        num_heroes: int = 4,
        seed: int | None = None,
        observation_mode: str = "mixed",
        ruleset: str | dict[str, Any] | None = None,
        hero_roles: list[str] | None = None,
    ) -> DungeonGridObservation:
        self.rng.seed(seed)
        self.rules.rng = self.rng
        self.observation_mode = observation_mode
        self.state = self.grid.new_state(
            quest_id=quest_id,
            num_heroes=num_heroes,
            seed=seed,
            ruleset=ruleset,
            hero_roles=hero_roles,
        )
        self.hooks.call(self.state.quest_id, "on_load", HookContext(state=self.state, env=self))
        self.grid.update_monster_awareness(self.state, reason="initial_visibility")
        from .core.engine_runtime import EngineRuntime

        runtime = EngineRuntime(self.rules)
        self.rules._runtime = runtime
        runtime.rng = self.rng
        runtime.phase.start_hero_turn(self.state, self.state.active_agent())
        return self.observe(self.state.active_agent())

    def checkpoint_payload(self, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        """Return a true environment checkpoint payload.

        The payload is intentionally Python-native and pickle-backed by the helper
        methods below. It preserves full hidden state and RNG state, so restoring
        from it can continue the exact same trajectory after a process restart.
        """

        state = self._require_state()
        return {
            "version": CHECKPOINT_VERSION,
            "quest_dir": self.quest_dir,
            "observation_mode": self.observation_mode,
            "state": copy.deepcopy(state),
            "rng_state": self.rng.getstate(),
            "metadata": dict(metadata or {}),
        }

    def checkpoint_bytes(self, metadata: dict[str, Any] | None = None) -> bytes:
        return pickle.dumps(self.checkpoint_payload(metadata), protocol=pickle.HIGHEST_PROTOCOL)

    def checkpoint_base64(self, metadata: dict[str, Any] | None = None) -> str:
        return base64.b64encode(self.checkpoint_bytes(metadata)).decode("ascii")

    def save_checkpoint(
        self, path: str | Path, metadata: dict[str, Any] | None = None
    ) -> Path:
        checkpoint_path = Path(path)
        checkpoint_path.parent.mkdir(parents=True, exist_ok=True)
        checkpoint_path.write_bytes(self.checkpoint_bytes(metadata))
        return checkpoint_path

    def restore_checkpoint(self, checkpoint: bytes | str | dict[str, Any]) -> DungeonGridObservation:
        payload = self._decode_checkpoint(checkpoint)
        if payload.get("version") != CHECKPOINT_VERSION:
            raise ValueError("unsupported DungeonGrid checkpoint payload")
        checkpoint_quest_dir = (
            str(payload["quest_dir"]) if payload.get("quest_dir") is not None else None
        )
        if self.quest_dir != checkpoint_quest_dir:
            self.quest_dir = checkpoint_quest_dir
            self.grid = GridEngine(quest_dir=self.quest_dir)
            self.hooks = HookEngine(dungeon_dir=self.quest_dir)
            self.rules = RulesEngine(self.grid, self.rng)
            self.rules.hooks = self.hooks
            self.agent_engine = AgentEngine(self.grid, self.rules)
        self.state = copy.deepcopy(payload["state"])
        self.observation_mode = str(payload.get("observation_mode") or "mixed")
        self.rng.setstate(payload["rng_state"])
        self.rules.rng = self.rng
        self.rules.hooks = self.hooks
        from .core.engine_runtime import EngineRuntime

        runtime = EngineRuntime(self.rules)
        runtime.rng = self.rng
        self.rules._runtime = runtime
        return self.observe(self.state.active_agent())

    @classmethod
    def load_checkpoint(
        cls, path: str | Path, quest_dir: str | None = None
    ) -> DungeonGridEnvironment:
        env = cls(quest_dir=quest_dir)
        env.restore_checkpoint(Path(path).read_bytes())
        return env

    @classmethod
    def from_checkpoint(
        cls, checkpoint: bytes | str | dict[str, Any], quest_dir: str | None = None
    ) -> DungeonGridEnvironment:
        env = cls(quest_dir=quest_dir)
        env.restore_checkpoint(checkpoint)
        return env

    def _decode_checkpoint(self, checkpoint: bytes | str | dict[str, Any]) -> dict[str, Any]:
        if isinstance(checkpoint, dict):
            return checkpoint
        if isinstance(checkpoint, bytes):
            payload = pickle.loads(checkpoint)
        elif isinstance(checkpoint, str):
            try:
                payload = pickle.loads(base64.b64decode(checkpoint.encode("ascii")))
            except Exception:
                payload = pickle.loads(Path(checkpoint).read_bytes())
        else:
            raise TypeError(f"Unsupported checkpoint type: {type(checkpoint)!r}")
        if not isinstance(payload, dict):
            raise ValueError("DungeonGrid checkpoint did not decode to a payload")
        return payload

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

    def step(
        self,
        action: DungeonGridAction | dict[str, Any],
        agent_id: str | None = None,
        *,
        _record_action_stats: bool = True,
    ) -> DungeonGridStep:
        state = self._require_state()
        action_dict = model_to_dict(action)
        resolved_agent = agent_id or action_dict.pop("agent_id", None) or state.active_agent()
        obs_before = model_to_dict(self.observe(resolved_agent))
        state_before = self.private_state_json()
        achievement_before = self.achievements.snapshot(state)
        trace_len_before = len(state.trace)
        reward, narration, info = self.rules.apply_action(state, resolved_agent, action_dict)
        effect_trace_entries = state.trace[trace_len_before:]
        awareness_events = self.grid.update_monster_awareness(
            state, reason=str(action_dict.get("type", "action"))
        )
        if awareness_events:
            info = {
                **info,
                "awareness_events": awareness_events,
            }
        new_achievement_reward, new_achievements = self.achievements.unlock_new(
            state,
            before=achievement_before,
        )
        if new_achievements:
            reward += max(0.0, new_achievement_reward)
            info = {
                **info,
                "achievement_reward": round(max(0.0, new_achievement_reward), 4),
                "new_achievements": new_achievements,
            }
        reward = max(0.0, reward)
        info = {**info, "narration": narration}
        if narration:
            state.event_log.append(narration)
        if not info.get("invalid"):
            self._clear_resolved_invalid_feedback(resolved_agent, action_dict)
        obs_after = self.observe(state.active_agent() if not state.done else resolved_agent)
        state_after = self.private_state_json()
        if resolved_agent in state.heroes:
            if _record_action_stats:
                self._record_hero_action_stats(
                    resolved_agent,
                    submitted=1,
                    executed=0 if info.get("invalid") else 1,
                    skipped=1 if info.get("invalid") else 0,
                    unused=0,
                )
            self._record_hero_reward(resolved_agent, reward, source="step")
            self._record_hero_reveal_stats(resolved_agent, state_before, state_after)
            self._record_hero_effect_stats(resolved_agent, action_dict, effect_trace_entries)
            for event in info.get("new_achievements", []):
                self._record_hero_achievement(resolved_agent, event)
        record = trace_record(
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
        record["observation_text"] = obs_before.get("text", "")
        for field in WARDEN_REASONING_FIELDS:
            if field in action_dict:
                record[field] = action_dict[field]
        if info.get("new_achievements"):
            record["new_achievements"] = info["new_achievements"]
        if resolved_agent in state.heroes:
            record["reward_attribution"] = {
                resolved_agent: {
                    "reward": round(reward, 4),
                    "new_achievements": [
                        event.get("id") for event in info.get("new_achievements", [])
                    ],
                }
            }
        state.trace.append(record)
        return DungeonGridStep(observation=obs_after, reward=reward, done=state.done, info=info)

    def observe_warden(self) -> dict[str, Any]:
        """Return the private/eval Warden observation used by Warden policies."""

        return build_warden_observation(self)

    def act_plan(
        self,
        actions: list[dict[str, Any]],
        intent: str | None = None,
        agent_id: str | None = None,
    ) -> DungeonGridPlanResult:
        state = self._require_state()
        resolved_agent = agent_id or state.active_agent()
        plan_observation = model_to_dict(self.observe(resolved_agent))
        submitted_actions = [dict(action) for action in actions]
        executed_actions: list[dict[str, Any]] = []
        skipped_actions: list[dict[str, Any]] = []
        unused_actions: list[dict[str, Any]] = []
        total_reward = 0.0
        plan_new_achievements: list[dict[str, Any]] = []
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
            step = self.step(action, agent_id=resolved_agent, _record_action_stats=False)
            total_reward += step.reward
            plan_new_achievements.extend(step.info.get("new_achievements", []))
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
            new_achievements=plan_new_achievements,
            done=state.done,
            observation=observation,
        )
        if resolved_agent in state.heroes:
            self._record_hero_action_stats(
                resolved_agent,
                submitted=len(submitted_actions),
                executed=len(executed_actions),
                skipped=len(skipped_actions),
                unused=len(unused_actions),
            )
        state.trace.append(
            {
                "kind": "plan",
                "round": state.round,
                "agent_id": resolved_agent,
                "intent": intent,
                "observation_text": plan_observation.get("text", ""),
                "submitted_actions": submitted_actions,
                "executed_actions": executed_actions,
                "skipped_actions": skipped_actions,
                "unused_actions": unused_actions,
                "reveal_stopped": reveal_stopped,
                "reveal_reason": reveal_reason,
                "reward": round(total_reward, 4),
                "new_achievements": plan_new_achievements,
                "reward_attribution": {
                    resolved_agent: {
                        "reward": round(total_reward, 4),
                        "new_achievements": [
                            event.get("id") for event in plan_new_achievements
                        ],
                    }
                }
                if resolved_agent in state.heroes
                else {},
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
            if state.ruleset:
                movement = state.movement_remaining.get(agent_id, 0)
                movement_roll = state.movement_rolls.get(agent_id, 0)
                major = "used" if state.major_action_used.get(agent_id) else "available"
                lines.append(
                    f"Classic rules: movement {movement}/{movement_roll}; major action {major}."
                )
            if hero.equipment:
                lines.append(f"Equipment: {self._equipment_summary(hero.equipment)}.")
            available_spells = self._available_spell_cards(hero.equipment)
            used_spells = [str(card) for card in hero.equipment.get("used_spell_cards", [])]
            if available_spells or used_spells:
                lines.append(
                    f"Spell cards: available={available_spells or ['none']}; "
                    f"used={used_spells or ['none']}."
                )
            if hero.status:
                lines.append(f"Active statuses: {hero.status}.")
        lines.append("")
        lines.append(self._quest_brief())
        lines.append(self._objective_instruction())
        roster = self._party_roster()
        if roster:
            lines.append("\nParty roster:")
            for member in roster:
                status = "alive" if member["alive"] else "down"
                lines.append(
                    f"- {member['id']}: {member['role']} hp {member['hp']}/{member['max_hp']} "
                    f"{status}"
                )
        visible_teammates = self._visible_teammates(agent_id)
        if visible_teammates:
            lines.append("\nVisible teammates:")
            for teammate in visible_teammates:
                lines.append(
                    f"- {teammate['id']} ({teammate['role']}) at {teammate['pos']} "
                    f"hp {teammate['hp']}/{teammate['max_hp']} "
                    f"equipment {teammate.get('equipment_summary', 'none')} "
                    f"spells {teammate.get('spell_cards', ['none'])}"
                )
        adjacent_tiles = self._adjacent_tiles(agent_id)
        if adjacent_tiles:
            lines.append("\nAdjacent tiles:")
            for tile in adjacent_tiles:
                detail = f", {tile['detail']}" if tile.get("detail") else ""
                lines.append(f"- {tile['direction']}: {tile['status']} at {tile['pos']}{detail}")
        lines.append("\nVisible map:")
        lines.append(self._coordinate_map(visible_map))
        lines.append(
            "\nLegend: B/W/E/D heroes, g/b/k/r/w/p/n/m/f/y/h monsters, D closed door, / open door, C chest, A/a/d/v/l/s/$/f furniture, T revealed trap, I objective, E exit."
        )
        visible_rooms = self._visible_rooms(agent_id)
        if visible_rooms:
            lines.append("\nVisible rooms:")
            for room in visible_rooms:
                lines.append(f"- {room['name']}: {room.get('description', '')}")
        visible_entities = self._visible_entities(agent_id)
        visible_objects = self._visible_objects(agent_id)
        if visible_entities:
            lines.append("\nVisible entities:")
            for ent in visible_entities:
                if ent["id"] != agent_id:
                    distance = (
                        f", distance {ent['distance']}" if ent.get("distance") is not None else ""
                    )
                    combat = f", {ent['combat_affordance']}" if ent.get("combat_affordance") else ""
                    boss = ""
                    if ent.get("boss"):
                        hint = (
                            f", hint={ent['boss_counterplay_hint']}"
                            if ent.get("boss_counterplay_hint")
                            else ""
                        )
                        boss = f", boss={ent.get('boss_name', ent['role'])} phase={ent.get('boss_phase', 'base')}{hint}"
                    statuses = f", status={ent.get('status')}" if ent.get("status") else ""
                    lines.append(
                        f"- {ent['id']} ({ent['role']}) at {ent['pos']} "
                        f"hp {ent['hp']}/{ent['max_hp']}{distance}{combat}{boss}{statuses}"
                    )
                    if ent.get("boss_summary"):
                        lines.append(f"  Boss rule: {ent['boss_summary']}")
        if visible_objects:
            lines.append("\nVisible objects:")
            for obj in visible_objects:
                label = obj.get("id", obj.get("type"))
                detail = f", {obj['affordance']}" if obj.get("affordance") else ""
                distance = (
                    f", distance {obj['distance']}" if obj.get("distance") is not None else ""
                )
                hint = f" Hint: {obj['action_hint']}" if obj.get("action_hint") else ""
                lines.append(
                    f"- {obj['type']} {label} at {obj.get('pos')}{distance}{detail}.{hint}"
                )
        carrier = state.objective.carrier or "not carried"
        lines.append(
            f"\nObjective: recover {state.objective.id} and reach {list(state.escape_tile)}. Carrier: {carrier}."
        )
        lines.append(self._escape_instruction())
        if state.ruleset and state.ruleset.get("extraction", {}).get("enabled"):
            extracted = sorted(state.extracted_heroes)
            lines.append(
                f"Extraction: extracted={extracted or ['none']}; "
                f"termination={state.termination_reason or 'not_terminal'}."
            )
        if state.event_log:
            lines.append("\nRecent events:")
            for event in state.event_log[-3:]:
                lines.append(f"- {event}")
        recent_draws = self._recent_card_draws()
        if recent_draws:
            lines.append("\nRecent known card draws:")
            for draw in recent_draws[-3:]:
                lines.append(
                    f"- {draw.get('deck')}: {draw.get('card_name')} ({draw.get('card_type')})"
                )
        if state.party_messages:
            lines.append("\nRecent party messages:")
            for message in state.party_messages[-5:]:
                lines.append(
                    f"- {message.get('from')} -> {message.get('to')}: {message.get('text')}"
                )
        if state.invalid_feedback:
            scoped_feedback = self._invalid_feedback_for_agent(agent_id)
        else:
            scoped_feedback = []
        if scoped_feedback:
            lines.append("\nPrevious invalid actions to correct:")
            for feedback in scoped_feedback[-3:]:
                lines.append(
                    f"- {feedback.get('agent_id')} at {feedback.get('position')}: "
                    f"action={feedback.get('action')} "
                    f"failed with {feedback.get('reason')} - {feedback.get('message')}"
                )
        if state.achievement_events:
            lines.append("\nRecent achievements:")
            for event in state.achievement_events[-5:]:
                lines.append(f"- {event.get('id')}: {event.get('title')} (+{event.get('reward')})")
        lines.append(
            "\nSubmit structured JSON actions with dungeongrid_act. "
            "Use dungeongrid_rules for action schemas and rule details."
        )
        return "\n".join(lines)

    def render_ascii(self, agent_id: str | None = None) -> str:
        return self.grid.render_ascii(self._require_state(), agent_id=agent_id)

    def state_json(self, visibility: str = "omniscient") -> dict[str, Any]:
        """Compatibility wrapper for explicit public/private state objects.

        Prefer private_state_json() for full engine state and public_state_json()
        for player/replay-visible state. This wrapper remains for existing
        callers that still pass visibility strings.
        """
        if visibility in {"omniscient", "private"}:
            return self.private_state_json()
        return self.public_state_json(visibility=visibility)

    def private_state_json(self) -> dict[str, Any]:
        state = self._require_state()
        return state.to_dict(visibility="private")

    def public_state_json(self, visibility: str = "party") -> dict[str, Any]:
        """Return only state that players/replays may know.

        Hidden deck order, chest contents, trap positions, furniture scripts,
        dormant monsters, and other Warden-private details are omitted or
        summarized. Use private_state_json() for debugging/evaluation internals.
        """
        state = self._require_state()
        data = state.to_dict(visibility=visibility)
        if visibility != "warden":
            visible = self.grid.visible_tiles(state, "party")
            data["monsters"] = {
                monster_id: self._public_monster_state(monster)
                for monster_id, monster in data["monsters"].items()
                if tuple(monster.get("pos", [])) in visible
                and monster.get("activation") != "dormant"
            }
            for trap in data["traps"].values():
                if not trap["revealed"]:
                    trap.pop("pos", None)
            for chest in data["chests"].values():
                chest.pop("contents", None)
            for item in data.get("furniture", {}).values():
                item.pop("deck", None)
                item.pop("search_effects", None)
                item.pop("break_effect", None)
            data["decks"] = {deck_id: "redacted" for deck_id in data.get("decks", {})}
            data["discards"] = {
                deck_id: [
                    {
                        "id": card.get("id"),
                        "name": card.get("name", card.get("id")),
                        "type": card.get("type"),
                    }
                    for card in cards
                    if isinstance(card, dict)
                ]
                for deck_id, cards in state.discards.items()
            }
            data["recent_card_draws"] = self._recent_card_draws()
            data["objective"] = self._public_objective_state(visible_tiles=visible)
            data["ruleset"] = {"enabled": bool(state.ruleset)}
            data["dread"] = None
            data["social_metrics"] = {
                "items_given": state.social_metrics.get("items_given", 0),
                "objective_passes": state.social_metrics.get("objective_passes", 0),
                "split_party_rounds": state.social_metrics.get("split_party_rounds", 0),
            }
            data["per_hero_stats"] = self._public_per_hero_stats(data.get("per_hero_stats", {}))
        return data

    def _public_per_hero_stats(self, per_hero_stats: dict[str, Any]) -> dict[str, Any]:
        public: dict[str, Any] = {}
        for hero_id, raw_stats in per_hero_stats.items():
            if not isinstance(raw_stats, dict):
                continue
            public[str(hero_id)] = {
                "role": raw_stats.get("role", ""),
                "reward": round(float(raw_stats.get("reward", 0.0) or 0.0), 4),
                "actions_executed": int(raw_stats.get("actions_executed", 0) or 0),
                "invalid_actions": int(raw_stats.get("invalid_actions", 0) or 0),
                "achievement_count": len(raw_stats.get("achievements_unlocked", []) or []),
                "damage_dealt": int(raw_stats.get("damage_dealt", 0) or 0),
                "damage_taken": int(raw_stats.get("damage_taken", 0) or 0),
                "monsters_defeated": int(raw_stats.get("monsters_defeated", 0) or 0),
                "tiles_revealed": int(raw_stats.get("tiles_revealed", 0) or 0),
                "rooms_revealed": int(raw_stats.get("rooms_revealed", 0) or 0),
                "messages_sent": int(raw_stats.get("messages_sent", 0) or 0),
                "treasure": int(raw_stats.get("treasure", 0) or 0),
                "extracted": bool(raw_stats.get("extracted", False)),
            }
        return public

    def _public_monster_state(self, monster: dict[str, Any]) -> dict[str, Any]:
        row = dict(monster)
        equipment = row.pop("equipment", {})
        if isinstance(equipment, dict) and equipment.get("boss"):
            row["boss"] = True
            row["boss_name"] = equipment.get("boss_name", row.get("role"))
            row["boss_phase"] = (equipment.get("triggered_phases") or ["base"])[-1]
            if equipment.get("public_summary"):
                row["boss_summary"] = equipment["public_summary"]
            if equipment.get("counterplay_hint"):
                row["boss_counterplay_hint"] = equipment["counterplay_hint"]
        return row

    def export_trace(self) -> dict[str, Any]:
        state = self._require_state()
        return {
            "quest_id": state.quest_id,
            "title": state.title,
            "trace": list(state.trace),
            "metrics": self.agent_engine.metrics(state),
        }

    def export_transcript(self) -> dict[str, Any]:
        """Return a compact LLM-reviewable transcript for the current run."""
        state = self._require_state()
        turns: list[dict[str, Any]] = []
        for record in state.trace:
            if record.get("kind") == "card_draw":
                turns.append(
                    {
                        "kind": "card_draw",
                        "round": record.get("round"),
                        "deck": record.get("deck"),
                        "card": record.get("card", {}).get("id"),
                    }
                )
                continue
            if record.get("kind") == "plan":
                turns.append(
                    {
                        "kind": "plan",
                        "round": record.get("round"),
                        "agent_id": record.get("agent_id"),
                        "intent": record.get("intent"),
                        "observation": record.get("observation_text", ""),
                        "submitted_actions": record.get("submitted_actions", []),
                        "executed_actions": record.get("executed_actions", []),
                        "skipped_actions": record.get("skipped_actions", []),
                        "unused_actions": record.get("unused_actions", []),
                        "reveal_reason": record.get("reveal_reason"),
                        "new_achievements": record.get("new_achievements", []),
                    "reward": record.get("reward", 0.0),
                    "reward_attribution": record.get("reward_attribution", {}),
                }
            )
            continue
            warden_reasoning = {
                field: record[field] for field in WARDEN_REASONING_FIELDS if field in record
            }
            turns.append(
                {
                    "kind": "action",
                    "round": record.get("round"),
                    "phase": record.get("phase"),
                    "agent_id": record.get("agent_id"),
                    "observation": record.get("observation_text", ""),
                    "action": record.get("action"),
                    "narration": record.get("narration", ""),
                    "new_achievements": record.get("new_achievements", []),
                    "violations": record.get("violations", []),
                    "reward": record.get("reward", 0.0),
                    "reward_attribution": record.get("reward_attribution", {}),
                    **warden_reasoning,
                }
            )
        return {
            "quest_id": state.quest_id,
            "title": state.title,
            "round": state.round,
            "winner": state.winner,
            "done": state.done,
            "metrics": self.agent_engine.metrics(state),
            "per_hero_stats": self.agent_engine.metrics(state).get("per_hero_stats", {}),
            "event_log": list(state.event_log),
            "party_messages": list(state.party_messages),
            "achievements": list(state.achievement_events),
            "turns": turns,
        }

    def _hero_stats(self, hero_id: str) -> dict[str, Any]:
        state = self._require_state()
        hero = state.heroes.get(hero_id)
        stats = state.per_hero_stats.setdefault(
            hero_id, default_per_hero_stats(hero, role=hero.role if hero else "")
        )
        if hero:
            stats["role"] = hero.role
            stats["extracted"] = hero_id in state.extracted_heroes
            stats["treasure"] = int(state.hero_treasure.get(hero_id, stats.get("treasure", 0)))
        return stats

    def _record_hero_action_stats(
        self,
        hero_id: str,
        *,
        submitted: int,
        executed: int,
        skipped: int,
        unused: int,
    ) -> None:
        stats = self._hero_stats(hero_id)
        stats["actions_submitted"] = int(stats.get("actions_submitted", 0)) + max(0, submitted)
        stats["actions_executed"] = int(stats.get("actions_executed", 0)) + max(0, executed)
        stats["invalid_actions"] = int(stats.get("invalid_actions", 0)) + max(0, skipped)
        stats["unused_actions"] = int(stats.get("unused_actions", 0)) + max(0, unused)

    def _record_hero_reward(self, hero_id: str, amount: float, *, source: str) -> None:
        if amount <= 0:
            return
        stats = self._hero_stats(hero_id)
        stats["reward"] = round(float(stats.get("reward", 0.0)) + max(0.0, amount), 4)
        reward_sources = stats.setdefault("reward_sources", {})
        reward_sources[source] = round(float(reward_sources.get(source, 0.0)) + amount, 4)

    def _record_hero_achievement(self, hero_id: str, event: dict[str, Any]) -> None:
        achievement_id = str(event.get("id") or "")
        if not achievement_id:
            return
        stats = self._hero_stats(hero_id)
        unlocked = list(stats.get("achievements_unlocked", []))
        if achievement_id not in unlocked:
            unlocked.append(achievement_id)
        stats["achievements_unlocked"] = unlocked
        stats["achievement_reward"] = round(
            float(stats.get("achievement_reward", 0.0))
            + max(0.0, float(event.get("reward", 0.0) or 0.0)),
            4,
        )
        stats.setdefault("achievement_events", []).append(
            {
                "id": achievement_id,
                "title": event.get("title"),
                "reward": max(0.0, float(event.get("reward", 0.0) or 0.0)),
                "team_achievement": True,
            }
        )

    def _record_hero_reveal_stats(
        self,
        hero_id: str,
        state_before: dict[str, Any],
        state_after: dict[str, Any],
    ) -> None:
        before_tiles = {
            tuple(pos)
            for pos in state_before.get("known_tiles", [])
            if isinstance(pos, list) and len(pos) == 2
        }
        after_tiles = {
            tuple(pos)
            for pos in state_after.get("known_tiles", [])
            if isinstance(pos, list) and len(pos) == 2
        }
        before_rooms = set(state_before.get("revealed_rooms", []))
        after_rooms = set(state_after.get("revealed_rooms", []))
        stats = self._hero_stats(hero_id)
        stats["tiles_revealed"] = int(stats.get("tiles_revealed", 0)) + max(
            0, len(after_tiles - before_tiles)
        )
        stats["rooms_revealed"] = int(stats.get("rooms_revealed", 0)) + max(
            0, len(after_rooms - before_rooms)
        )

    def _record_hero_effect_stats(
        self,
        hero_id: str,
        action: dict[str, Any],
        trace_entries: list[dict[str, Any]],
    ) -> None:
        stats = self._hero_stats(hero_id)
        action_type = str(action.get("type", ""))
        if action_type == "cast":
            stats["spell_casts"] = int(stats.get("spell_casts", 0)) + 1
        if action_type.startswith("search_") or action_type in {"inspect_tile", "inspect_room"}:
            stats["searches"] = int(stats.get("searches", 0)) + 1
        for entry in trace_entries:
            if entry.get("kind") == "spell_used" and entry.get("agent_id") == hero_id:
                stats["spell_casts"] = max(1, int(stats.get("spell_casts", 0)))
            if entry.get("kind") == "search" and entry.get("agent_id") == hero_id:
                stats["searches"] = max(1, int(stats.get("searches", 0)))

    def _symbolic_observation(self, agent_id: str, visible_map: str) -> dict[str, Any]:
        state = self._require_state()
        visible_tiles = self.grid.visible_tiles(state, agent_id)
        visible_entities = self._visible_entities(agent_id)
        visible_objects = self._visible_objects(agent_id)
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
            "visible_rooms": self._visible_rooms(agent_id),
            "party_roster": self._party_roster(),
            "visible_teammates": self._visible_teammates(agent_id),
            "adjacent_tiles": self._adjacent_tiles(agent_id),
            "visible_map": visible_map,
            "visible_map_coordinates": self._coordinate_map(visible_map),
            "quest_title": state.title,
            "quest_brief": self._quest_brief(),
            "objective": self._public_objective_state(visible_tiles=visible_tiles),
            "known_objective": f"recover_{state.objective.id}_and_escape",
            "objective_instruction": self._objective_instruction(),
            "escape_instruction": self._escape_instruction(),
            "party_messages": list(state.party_messages[-10:]),
            "invalid_feedback": self._invalid_feedback_for_agent(agent_id)[-5:],
            "recent_card_draws": self._recent_card_draws(),
            "movement_remaining": state.movement_remaining.get(agent_id, 0),
            "movement_roll": state.movement_rolls.get(agent_id, 0),
            "major_action_used": state.major_action_used.get(agent_id, False),
            "ruleset_enabled": bool(state.ruleset),
            "extracted_heroes": sorted(state.extracted_heroes),
            "termination_reason": state.termination_reason,
            "known_discards": {
                deck_id: [
                    {
                        "id": card.get("id"),
                        "name": card.get("name", card.get("id")),
                        "type": card.get("type"),
                    }
                    for card in cards
                    if isinstance(card, dict)
                ]
                for deck_id, cards in state.discards.items()
            },
            "achievements_unlocked": sorted(state.achievements_unlocked),
            "achievement_events": list(state.achievement_events[-10:]),
            "achievement_reward": round(state.achievement_reward, 4),
            "alert": state.alert if agent_id == "warden" else None,
            "torch": state.torch,
        }

    def _quest_brief(self) -> str:
        state = self._require_state()
        item_name = self._humanize_id(state.objective.id)
        return (
            f"Quest brief: recover the {item_name} from the dungeon, then bring the "
            f"carrier back to the escape tile at {list(state.escape_tile)}. Explore "
            "unopened doors and unrevealed rooms until the objective glyph I is visible."
        )

    def _objective_instruction(self) -> str:
        state = self._require_state()
        return (
            f"Objective action: when adjacent to the objective glyph I, use "
            f'{{"type":"interact","target":"{state.objective.id}"}} to pick it up.'
        )

    def _escape_instruction(self) -> str:
        state = self._require_state()
        return (
            f"Escape action: when the carrier is on {list(state.escape_tile)}, use "
            '{"type":"interact","target":"escape"}. If that succeeds, the episode ends '
            "immediately and no further hero or Warden steps run."
        )

    def _public_objective_state(
        self, visible_tiles: set[tuple[int, int]] | None = None
    ) -> dict[str, Any]:
        state = self._require_state()
        objective = state.objective
        data: dict[str, Any] = {
            "id": objective.id,
            "carrier": objective.carrier,
            "recovered": objective.recovered,
            "fragile": objective.fragile,
            "visible": False,
            "location_known": bool(objective.carrier or objective.recovered),
        }
        if objective.recovered:
            data["location_state"] = "recovered"
            return data
        if objective.carrier:
            data["location_state"] = "carried"
            return data
        if objective.pos is not None and visible_tiles is not None and objective.pos in visible_tiles:
            data["pos"] = list(objective.pos)
            data["visible"] = True
            data["location_known"] = True
            data["location_state"] = "visible_on_map"
            return data
        data["location_state"] = "hidden_or_unseen"
        return data

    def _humanize_id(self, value: str) -> str:
        return str(value).replace("_", " ").strip().title() or "Objective"

    def _visible_objects(self, agent_id: str) -> list[dict[str, Any]]:
        state = self._require_state()
        objects = self.grid.visible_objects(state, agent_id)
        hero = state.heroes.get(agent_id)
        if not hero:
            return objects
        enriched: list[dict[str, Any]] = []
        for obj in objects:
            row = dict(obj)
            pos_raw = row.get("pos")
            pos = (
                tuple(pos_raw) if isinstance(pos_raw, (list, tuple)) and len(pos_raw) == 2 else None
            )
            distance = self.grid.manhattan(hero.pos, pos) if pos is not None else None
            row["distance"] = distance
            row["adjacent"] = distance is not None and distance <= 1
            row["affordance"] = self._object_affordance(row, adjacent=bool(row["adjacent"]))
            row["action_hint"] = self._object_action_hint(row)
            enriched.append(row)
        return enriched

    def _coordinate_map(self, visible_map: str) -> str:
        rows = visible_map.splitlines()
        if not rows:
            return visible_map
        width = max(len(row) for row in rows)
        tens = "".join(str((idx // 10) % 10) if idx >= 10 else " " for idx in range(width))
        ones = "".join(str(idx % 10) for idx in range(width))
        labeled = [f"    {tens}", f"    {ones}"]
        labeled.extend(f"{y:02d}: {row}" for y, row in enumerate(rows))
        return "\n".join(labeled)

    def _visible_entities(self, agent_id: str) -> list[dict[str, Any]]:
        state = self._require_state()
        entities = self.grid.visible_entities(state, agent_id)
        hero = state.heroes.get(agent_id)
        if not hero:
            return entities
        ap = state.ap_remaining.get(agent_id, 0)
        enriched: list[dict[str, Any]] = []
        for entity in entities:
            row = dict(entity)
            pos_raw = row.get("pos")
            pos = (
                tuple(pos_raw) if isinstance(pos_raw, (list, tuple)) and len(pos_raw) == 2 else None
            )
            distance = self.grid.manhattan(hero.pos, pos) if pos is not None else None
            row["distance"] = distance
            row["adjacent"] = distance == 1
            if row.get("team") == "dungeon":
                if ap < 2:
                    row["combat_affordance"] = "visible_enemy_insufficient_ap"
                elif distance == 1:
                    row["combat_affordance"] = "attack_melee_available"
                elif (
                    distance is not None
                    and distance <= 5
                    and self.grid.line_clear(state, hero.pos, pos)
                ):
                    row["combat_affordance"] = "attack_ranged_available"
                else:
                    row["combat_affordance"] = "visible_enemy_not_attackable_from_here"
            enriched.append(row)
        return enriched

    def _object_affordance(self, obj: dict[str, Any], *, adjacent: bool) -> str:
        obj_type = str(obj.get("type") or "")
        if obj_type == "door":
            state = str(obj.get("state") or "")
            if state == "closed":
                return (
                    "open_door_available: use open_door target id"
                    if adjacent
                    else "visible_closed_door_not_adjacent: move adjacent before open_door"
                )
            if state == "open":
                return "already_open_passage: move through clear adjacent floor tiles"
            return f"door_state_{state or 'unknown'}"
        if obj_type == "furniture":
            if obj.get("destroyed"):
                return "destroyed"
            options = []
            searched = set(obj.get("searched_categories") or [])
            if adjacent and "furniture" not in searched:
                options.append("search_furniture_available")
            if adjacent and "treasure" not in searched:
                options.append("search_treasure_available")
            if adjacent and obj.get("destructible"):
                options.append("attack_object_available")
            return (
                "+".join(options)
                if options
                else (
                    "visible_furniture_searched: no remaining obvious search"
                    if adjacent
                    else "visible_not_adjacent: move adjacent before search/interact"
                )
            )
        if obj_type == "chest":
            return (
                "search_treasure_available: use search_treasure target id"
                if adjacent
                else "visible_not_adjacent: move adjacent before search_treasure"
            )
        if obj_type == "objective":
            return (
                "interact_available: use interact target objective id now"
                if adjacent
                else "visible_not_adjacent: move adjacent before interact"
            )
        if obj_type == "trap":
            armed = bool(obj.get("armed"))
            return (
                "disarm_available: use disarm target id"
                if armed and adjacent
                else "visible_trap: avoid or move adjacent to disarm"
            )
        return "visible"

    def _object_action_hint(self, obj: dict[str, Any]) -> str:
        obj_type = str(obj.get("type") or "")
        target = obj.get("id", obj_type)
        if obj_type == "objective":
            if obj.get("adjacent"):
                return f'Now legal: {{"type":"interact","target":"{target}"}}.'
            return "Not adjacent yet: move onto a neighboring open tile before interacting."
        if obj_type == "door":
            if obj.get("state") == "closed" and obj.get("adjacent"):
                return f'Now legal: {{"type":"open_door","target":"{target}"}}.'
            if obj.get("state") == "closed":
                return "Not adjacent yet: move next to the door before opening it."
            return "Door is open: move through the passage, do not open it again."
        if obj_type in {"furniture", "chest"}:
            if obj.get("adjacent"):
                return f"Adjacent: search or interact using target {target} if the affordance says available."
            return "Not adjacent yet: move next to it before search/interact actions."
        if obj_type == "trap":
            if obj.get("armed") and obj.get("adjacent"):
                return f'Now legal: {{"type":"disarm","target":"{target}"}}.'
            return "Visible trap: avoid stepping on it; move adjacent before disarming."
        return ""

    def _invalid_feedback_for_agent(self, agent_id: str) -> list[dict[str, Any]]:
        state = self._require_state()
        hero = state.heroes.get(agent_id)
        current_pos = list(hero.pos) if hero else None
        return [
            feedback
            for feedback in state.invalid_feedback[-10:]
            if feedback.get("agent_id") == agent_id
            and (
                feedback.get("position") is None
                or current_pos is None
                or feedback.get("position") == current_pos
            )
        ]

    def _clear_resolved_invalid_feedback(self, agent_id: str, action: dict[str, Any]) -> None:
        state = self._require_state()
        key = self._action_feedback_key(action)
        state.invalid_feedback = [
            feedback
            for feedback in state.invalid_feedback
            if feedback.get("agent_id") != agent_id
            or self._action_feedback_key(feedback.get("action") or {}) != key
        ]

    def _action_feedback_key(self, action: dict[str, Any]) -> tuple[Any, ...]:
        return (
            action.get("type"),
            action.get("direction"),
            action.get("target"),
        )

    def _party_roster(self) -> list[dict[str, Any]]:
        state = self._require_state()
        roster: list[dict[str, Any]] = []
        for hero_id in state.hero_order:
            hero = state.heroes.get(hero_id)
            if not hero:
                continue
            roster.append(
                {
                    "id": hero.id,
                    "role": hero.role,
                    "hp": hero.hp,
                    "max_hp": hero.max_hp,
                    "alive": hero.alive,
                }
            )
        return roster

    def _visible_teammates(self, agent_id: str) -> list[dict[str, Any]]:
        state = self._require_state()
        if agent_id not in state.heroes:
            return []
        visible = self.grid.visible_tiles(state, agent_id)
        teammates: list[dict[str, Any]] = []
        for hero_id in state.hero_order:
            if hero_id == agent_id:
                continue
            hero = state.heroes.get(hero_id)
            if not hero or not hero.alive or hero.pos not in visible:
                continue
            teammates.append(
                {
                    "id": hero.id,
                    "role": hero.role,
                    "pos": list(hero.pos),
                    "hp": hero.hp,
                    "max_hp": hero.max_hp,
                    "inventory": list(hero.inventory),
                    "equipment": dict(hero.equipment),
                    "equipment_summary": self._equipment_summary(hero.equipment),
                    "spell_cards": self._available_spell_cards(hero.equipment),
                    "used_spell_cards": [
                        str(card) for card in hero.equipment.get("used_spell_cards", [])
                    ],
                    "status": list(hero.status),
                }
            )
        return teammates

    def _equipment_summary(self, equipment: dict[str, Any]) -> str:
        if not equipment:
            return "none"
        slot_order = ["weapon", "armor", "offhand", "cloak", "helm", "charm", "tool"]
        parts = [f"{slot}={equipment[slot]}" for slot in slot_order if equipment.get(slot)]
        parts.extend(
            f"{slot}={value}"
            for slot, value in sorted(equipment.items())
            if slot not in slot_order and slot not in {"spell_cards", "used_spell_cards"} and value
        )
        return ", ".join(parts) if parts else "none"

    def _available_spell_cards(self, equipment: dict[str, Any]) -> list[str]:
        used_counts: dict[str, int] = {}
        for card in equipment.get("used_spell_cards", []):
            key = str(card)
            used_counts[key] = used_counts.get(key, 0) + 1
        available: list[str] = []
        for card in equipment.get("spell_cards", []):
            key = str(card)
            if used_counts.get(key, 0) > 0:
                used_counts[key] -= 1
                continue
            available.append(key)
        return available

    def _recent_card_draws(self, limit: int = 8) -> list[dict[str, Any]]:
        state = self._require_state()
        draws: list[dict[str, Any]] = []
        for record in state.trace:
            if record.get("kind") != "card_draw":
                continue
            card = record.get("card") if isinstance(record.get("card"), dict) else {}
            draws.append(
                {
                    "round": record.get("round"),
                    "deck": record.get("deck"),
                    "card_id": card.get("id"),
                    "card_name": card.get("name", card.get("id")),
                    "card_type": card.get("type"),
                }
            )
        return draws[-limit:]

    def _adjacent_tiles(self, agent_id: str) -> list[dict[str, Any]]:
        state = self._require_state()
        hero = state.heroes.get(agent_id)
        if not hero:
            return []
        tiles: list[dict[str, Any]] = []
        for direction, (dx, dy) in DIRECTIONS.items():
            pos = (hero.pos[0] + dx, hero.pos[1] + dy)
            row: dict[str, Any] = {"direction": direction, "pos": list(pos)}
            if not self.grid.in_bounds(state, pos):
                row.update({"status": "blocked", "detail": "out_of_bounds"})
                tiles.append(row)
                continue
            entity = state.entity_at(pos)
            door = state.door_at(pos)
            if entity:
                row.update(
                    {"status": "blocked", "detail": f"occupied_by_{entity.id}_{entity.role}"}
                )
            elif door and door.secret and not door.discovered:
                row.update({"status": "blocked", "detail": "wall_or_undiscovered_secret"})
            elif door and door.state == "closed":
                row.update({"status": "door", "detail": f"closed door id={door.id}"})
            elif self.grid.is_wall(state, pos):
                row.update({"status": "blocked", "detail": "wall"})
            elif self.grid.is_walkable(state, pos):
                row.update({"status": "open", "detail": "walkable"})
            else:
                row.update({"status": "blocked", "detail": "not_walkable"})
            tiles.append(row)
        return tiles

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
            "chests": {
                chest_id: {"opened": chest.opened} for chest_id, chest in state.chests.items()
            },
            "furniture": {
                item_id: {
                    "searched": item.searched,
                    "searched_categories": sorted(item.searched_categories),
                    "hp": item.hp,
                    "destroyed": item.destroyed,
                }
                for item_id, item in state.furniture.items()
            },
            "objective": state.objective.to_dict(),
            "monster_status": {
                monster_id: list(monster.status) for monster_id, monster in state.monsters.items()
            },
            "boss_state": {
                monster_id: {
                    "hp": monster.hp,
                    "alive": monster.alive,
                    "phase": (monster.equipment.get("triggered_phases") or ["base"])[-1],
                }
                for monster_id, monster in state.monsters.items()
                if monster.equipment.get("boss")
            },
        }

    def _visible_rooms(self, agent_id: str) -> list[dict[str, Any]]:
        state = self._require_state()
        visible = self.grid.visible_tiles(state, agent_id)
        rooms: list[dict[str, Any]] = []
        for room_id, room in state.rooms.items():
            room_tiles = self._room_tiles(room)
            if not room_tiles or not (room_tiles & visible):
                continue
            rooms.append(
                {
                    "id": room_id,
                    "name": room.get("name", room_id),
                    "description": room.get("description", ""),
                    "tags": list(room.get("tags", [])),
                }
            )
        return rooms

    def _room_tiles(self, room: dict[str, Any]) -> set[tuple[int, int]]:
        if "tiles" in room:
            return {(int(pos[0]), int(pos[1])) for pos in room.get("tiles", [])}
        rect = room.get("rect")
        if isinstance(rect, list) and len(rect) == 4:
            x1, y1, x2, y2 = [int(value) for value in rect]
            return {(x, y) for y in range(y1, y2 + 1) for x in range(x1, x2 + 1)}
        return set()

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
        for item_id, before_item in before.get("furniture", {}).items():
            after_item = after.get("furniture", {}).get(item_id, {})
            if not before_item.get("searched") and after_item.get("searched"):
                return "furniture_searched"
            if before_item.get("searched_categories") != after_item.get("searched_categories"):
                return "furniture_searched"
            if not before_item.get("destroyed") and after_item.get("destroyed"):
                return "object_destroyed"
        if before.get("monster_status") != after.get("monster_status") or before.get(
            "boss_state"
        ) != after.get("boss_state"):
            return "boss_state_changed"
        if before["objective"] != after["objective"]:
            return "objective_changed"
        if before["active_agent"] != after["active_agent"] or before["phase"] != after["phase"]:
            return "turn_ended"
        return None

    def _require_state(self):
        if self.state is None:
            self.reset()
        return self.state
