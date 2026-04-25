"""OpenEnv-style DungeonGrid environment class."""

from __future__ import annotations

import random
from typing import Any

from .achievements import AchievementEngine
from .core.data import DIRECTIONS
from .core.agent_engine import AgentEngine
from .core.grid_engine import GridEngine
from .core.rules_engine import RulesEngine
from .core.trace import trace_record
from .hooks import HookContext, HookEngine
from .models import DungeonGridAction, DungeonGridObservation, DungeonGridPlanResult, DungeonGridStep, model_to_dict


class _OpenEnvEnvironment:
    """Minimal base class for the local OpenEnv-style API."""

    pass


class DungeonGridEnvironment(_OpenEnvEnvironment):
    """Text dungeon-crawl environment with an OpenEnv/Gym-like API.

    The public methods intentionally mirror the benchmark interface:
    reset, observe, step, act_plan, render_text, render_ascii, state_json, export_trace.
    """

    def __init__(self, quest_dir: str | None = None) -> None:
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
    ) -> DungeonGridObservation:
        self.rng.seed(seed)
        self.rules.rng = self.rng
        self.observation_mode = observation_mode
        self.state = self.grid.new_state(quest_id=quest_id, num_heroes=num_heroes, seed=seed)
        self.hooks.call(self.state.quest_id, "on_load", HookContext(state=self.state, env=self))
        self.grid.update_monster_awareness(self.state, reason="initial_visibility")
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
        state_before = self.private_state_json()
        achievement_before = self.achievements.snapshot(state)
        reward, narration, info = self.rules.apply_action(state, resolved_agent, action_dict)
        awareness_events = self.grid.update_monster_awareness(state, reason=str(action_dict.get("type", "action")))
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
            reward += new_achievement_reward
            info = {
                **info,
                "achievement_reward": round(new_achievement_reward, 4),
                "new_achievements": new_achievements,
            }
        info = {**info, "narration": narration}
        if narration:
            state.event_log.append(narration)
        if not info.get("invalid"):
            self._clear_resolved_invalid_feedback(resolved_agent, action_dict)
        obs_after = self.observe(state.active_agent() if not state.done else resolved_agent)
        state_after = self.private_state_json()
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
        if info.get("new_achievements"):
            record["new_achievements"] = info["new_achievements"]
        state.trace.append(record)
        return DungeonGridStep(observation=obs_after, reward=reward, done=state.done, info=info)

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
            step = self.step(action, agent_id=resolved_agent)
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
                lines.append(
                    f"- {tile['direction']}: {tile['status']} at {tile['pos']}{detail}"
                )
        lines.append("\nVisible map:")
        lines.append(self._coordinate_map(visible_map))
        lines.append("\nLegend: B/W/E/D heroes, g/b/k/r/w/p/n/m/f/y/h monsters, D closed door, / open door, C chest, A/a/d/v/l/s/$/f furniture, T revealed trap, I objective, E exit.")
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
                    distance = f", distance {ent['distance']}" if ent.get("distance") is not None else ""
                    combat = (
                        f", {ent['combat_affordance']}"
                        if ent.get("combat_affordance")
                        else ""
                    )
                    boss = ""
                    if ent.get("boss"):
                        hint = f", hint={ent['boss_counterplay_hint']}" if ent.get("boss_counterplay_hint") else ""
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
                distance = f", distance {obj['distance']}" if obj.get("distance") is not None else ""
                lines.append(f"- {obj['type']} {label} at {obj.get('pos')}{distance}{detail}")
        carrier = state.objective.carrier or "not carried"
        lines.append(f"\nObjective: recover {state.objective.id} and reach {list(state.escape_tile)}. Carrier: {carrier}.")
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
        return data

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
        return {"quest_id": state.quest_id, "title": state.title, "trace": list(state.trace), "metrics": self.agent_engine.metrics(state)}

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
                    }
                )
                continue
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
                }
            )
        return {
            "quest_id": state.quest_id,
            "title": state.title,
            "round": state.round,
            "winner": state.winner,
            "done": state.done,
            "metrics": self.agent_engine.metrics(state),
            "event_log": list(state.event_log),
            "party_messages": list(state.party_messages),
            "achievements": list(state.achievement_events),
            "turns": turns,
        }

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
            "objective": state.objective.to_dict(),
            "known_objective": f"recover_{state.objective.id}_and_escape",
            "party_messages": list(state.party_messages[-10:]),
            "invalid_feedback": self._invalid_feedback_for_agent(agent_id)[-5:],
            "recent_card_draws": self._recent_card_draws(),
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
                tuple(pos_raw)
                if isinstance(pos_raw, (list, tuple)) and len(pos_raw) == 2
                else None
            )
            distance = self.grid.manhattan(hero.pos, pos) if pos is not None else None
            row["distance"] = distance
            row["adjacent"] = distance is not None and distance <= 1
            row["affordance"] = self._object_affordance(row, adjacent=bool(row["adjacent"]))
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
                tuple(pos_raw)
                if isinstance(pos_raw, (list, tuple)) and len(pos_raw) == 2
                else None
            )
            distance = self.grid.manhattan(hero.pos, pos) if pos is not None else None
            row["distance"] = distance
            row["adjacent"] = distance == 1
            if row.get("team") == "dungeon":
                if ap < 2:
                    row["combat_affordance"] = "visible_enemy_insufficient_ap"
                elif distance == 1:
                    row["combat_affordance"] = "attack_melee_available"
                elif distance is not None and distance <= 5 and self.grid.line_clear(state, hero.pos, pos):
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
                return "open_door_available" if adjacent else "visible_closed_door_not_adjacent"
            if state == "open":
                return "already_open_passage"
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
            return "+".join(options) if options else ("visible_furniture_searched" if adjacent else "visible_not_adjacent")
        if obj_type == "chest":
            return "search_treasure_available" if adjacent else "visible_not_adjacent"
        if obj_type == "objective":
            return "interact_available" if adjacent else "visible_not_adjacent"
        if obj_type == "trap":
            armed = bool(obj.get("armed"))
            return "disarm_available" if armed and adjacent else "visible_trap"
        return "visible"

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
                    "used_spell_cards": [str(card) for card in hero.equipment.get("used_spell_cards", [])],
                    "status": list(hero.status),
                }
            )
        return teammates

    def _equipment_summary(self, equipment: dict[str, Any]) -> str:
        if not equipment:
            return "none"
        slot_order = ["weapon", "armor", "offhand", "cloak", "helm", "charm", "tool"]
        parts = [
            f"{slot}={equipment[slot]}"
            for slot in slot_order
            if equipment.get(slot)
        ]
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
                row.update({"status": "blocked", "detail": f"occupied_by_{entity.id}_{entity.role}"})
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
            "chests": {chest_id: {"opened": chest.opened} for chest_id, chest in state.chests.items()},
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
                monster_id: list(monster.status)
                for monster_id, monster in state.monsters.items()
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
        if before.get("monster_status") != after.get("monster_status") or before.get("boss_state") != after.get("boss_state"):
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
