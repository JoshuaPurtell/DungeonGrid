"""Achievement definitions and unlock logic for DungeonGrid runs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .core.data import GameState, Pos
else:
    GameState = Any
    Pos = tuple[int, int]


@dataclass(frozen=True, slots=True)
class Achievement:
    id: str
    title: str
    layer: str
    reward: float
    condition: dict[str, Any]
    description: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "layer": self.layer,
            "reward": self.reward,
            "condition": dict(self.condition),
            "description": self.description,
        }


GLOBAL_ACHIEVEMENTS: tuple[Achievement, ...] = (
    Achievement(
        id="exploration.first_room_revealed",
        title="First Room Revealed",
        layer="global",
        reward=0.10,
        condition={"type": "rooms_explored_at_least", "count": 2},
        description="Reveal a room beyond the starting area.",
    ),
    Achievement(
        id="exploration.ten_floor_tiles",
        title="Ten Floor Tiles Mapped",
        layer="global",
        reward=0.05,
        condition={"type": "known_floor_tiles_at_least", "count": 10},
        description="Map at least ten walkable floor tiles.",
    ),
    Achievement(
        id="coordination.message_sent",
        title="Party Message Sent",
        layer="global",
        reward=0.03,
        condition={"type": "messages_sent_at_least", "count": 1, "min_heroes": 2},
        description="Send a message to the party or another hero.",
    ),
    Achievement(
        id="doors.first_door_opened",
        title="First Door Opened",
        layer="global",
        reward=0.08,
        condition={"type": "door_opened"},
        description="Open any dungeon door.",
    ),
    Achievement(
        id="hazards.trap_revealed",
        title="Trap Revealed",
        layer="global",
        reward=0.08,
        condition={"type": "trap_revealed"},
        description="Reveal a hidden trap.",
    ),
    Achievement(
        id="hazards.trap_disarmed",
        title="Trap Disarmed",
        layer="global",
        reward=0.10,
        condition={"type": "trap_disarmed"},
        description="Disarm a revealed trap.",
    ),
    Achievement(
        id="treasure.first_chest_opened",
        title="First Chest Opened",
        layer="global",
        reward=0.08,
        condition={"type": "chest_opened"},
        description="Open any chest.",
    ),
    Achievement(
        id="treasure.first_treasure_collected",
        title="First Treasure Collected",
        layer="global",
        reward=0.08,
        condition={"type": "treasure_collected"},
        description="Collect treasure from a chest or cache.",
    ),
    Achievement(
        id="combat.first_monster_defeated",
        title="First Monster Defeated",
        layer="global",
        reward=0.10,
        condition={"type": "monster_defeated"},
        description="Defeat any dungeon monster.",
    ),
    Achievement(
        id="combat.new_roster_monster_defeated",
        title="New Roster Monster Defeated",
        layer="global",
        reward=0.08,
        condition={
            "type": "monster_defeated",
            "roles": [
                "rat_pack",
                "iron_sentinel",
                "tusk_mauler",
                "cinder_mage",
                "mirror_adept",
                "hollow_knight",
            ],
        },
        description="Defeat one of DungeonGrid's expanded monster archetypes.",
    ),
    Achievement(
        id="combat.survived_special_pressure",
        title="Survived Special Pressure",
        layer="global",
        reward=0.06,
        condition={
            "type": "trace_kind_happened",
            "kinds": ["monster_cleave", "monster_ranged_attack"],
        },
        description="Survive a cleave or ranged caster threat.",
    ),
    Achievement(
        id="combat.mirror_decoy_triggered",
        title="Mirror Decoy Broken",
        layer="global",
        reward=0.05,
        condition={"type": "trace_kind_happened", "kind": "monster_decoy_triggered"},
        description="Trigger a mirror adept's decoy.",
    ),
    Achievement(
        id="combat.hollow_knight_put_down",
        title="Hollow Knight Put Down",
        layer="global",
        reward=0.08,
        condition={"type": "revived_monster_defeated", "role": "hollow_knight"},
        description="Defeat a hollow knight after its revival has triggered.",
    ),
    Achievement(
        id="equipment.first_armor_equipped",
        title="First Armor Equipped",
        layer="global",
        reward=0.05,
        condition={"type": "trace_kind_happened", "kind": "armor_equipped"},
        description="Equip a defensive item.",
    ),
    Achievement(
        id="coordination.item_given",
        title="Item Given",
        layer="global",
        reward=0.05,
        condition={"type": "trace_kind_happened", "kind": "item_given"},
        description="Hand a carried item to an adjacent teammate.",
    ),
    Achievement(
        id="equipment.defensive_prevention",
        title="Defensive Gear Worked",
        layer="global",
        reward=0.07,
        condition={"type": "trace_kind_happened", "kind": "defensive_prevention"},
        description="Prevent damage or monster pressure with defensive gear.",
    ),
    Achievement(
        id="magic.first_spell_used",
        title="First Spell Used",
        layer="global",
        reward=0.05,
        condition={"type": "spell_used"},
        description="Cast a carried spell card.",
    ),
    Achievement(
        id="cards.first_card_drawn",
        title="First Card Drawn",
        layer="global",
        reward=0.05,
        condition={"type": "trace_kind_happened", "kind": "card_draw"},
        description="Resolve a dungeon deck card.",
    ),
    Achievement(
        id="classic.first_hero_extracted",
        title="First Hero Extracted",
        layer="global",
        reward=0.08,
        condition={"type": "extracted_heroes_at_least", "count": 1},
        description="Extract at least one hero from a classic-dynamic dungeon.",
    ),
    Achievement(
        id="classic.no_one_left_behind",
        title="No One Left Behind",
        layer="global",
        reward=0.18,
        condition={"type": "termination_reason", "reason": "full_party_extraction"},
        description="Finish with every submitted hero extracted.",
    ),
    Achievement(
        id="classic.partial_extraction",
        title="Partial Extraction",
        layer="global",
        reward=0.06,
        condition={"type": "termination_reason", "reason": "partial_extraction"},
        description="Secure the objective and call a partial extraction.",
    ),
    Achievement(
        id="classic.bad_treasure_survived",
        title="Bad Treasure Draw Survived",
        layer="global",
        reward=0.05,
        condition={
            "type": "social_metric_at_least",
            "metric": "wanderers_spawned_by_greed",
            "count": 1,
        },
        description="Trigger a risky treasure draw that spawns Warden pressure.",
    ),
    Achievement(
        id="objective.item_recovered",
        title="Objective Item Recovered",
        layer="global",
        reward=0.25,
        condition={"type": "objective_taken"},
        description="Pick up the dungeon objective item.",
    ),
    Achievement(
        id="objective.escaped_with_item",
        title="Escaped With Objective",
        layer="global",
        reward=0.50,
        condition={"type": "success"},
        description="Complete the dungeon objective and escape.",
    ),
    Achievement(
        id="survival.full_party_success",
        title="Full Party Survival",
        layer="global",
        reward=0.20,
        condition={"type": "all_heroes_survive_success"},
        description="Win with every submitted hero still alive.",
    ),
)


class AchievementEngine:
    """Evaluates one-time global and quest achievements for a run."""

    def definitions_for(self, state: GameState) -> list[Achievement]:
        return [*GLOBAL_ACHIEVEMENTS, *state.quest_achievement_defs]

    def snapshot(self, state: GameState) -> dict[str, Any]:
        return {
            "known_floor_tiles": self._known_floor_tiles(state),
            "rooms_explored": self._rooms_explored(state),
            "party_messages": len(state.party_messages),
            "treasure_collected": state.treasure_collected,
            "objective_carrier": state.objective.carrier,
            "objective_recovered": state.objective.recovered,
            "done": state.done,
            "winner": state.winner,
            "alert": state.alert,
            "living_heroes": len(state.living_heroes()),
            "hero_count": len(state.heroes),
            "doors": {
                door_id: {"state": door.state, "discovered": door.discovered}
                for door_id, door in state.doors.items()
            },
            "traps": {
                trap_id: {"armed": trap.armed, "revealed": trap.revealed}
                for trap_id, trap in state.traps.items()
            },
            "chests": {
                chest_id: {"opened": chest.opened} for chest_id, chest in state.chests.items()
            },
            "furniture": {
                item_id: {"searched": item.searched, "category": item.category}
                for item_id, item in state.furniture.items()
            },
            "monsters": {
                monster_id: {
                    "alive": monster.alive,
                    "role": monster.role,
                    "status": list(monster.status),
                }
                for monster_id, monster in state.monsters.items()
            },
            "trace_kind_counts": self._trace_kind_counts(state),
            "extracted_heroes": len(state.extracted_heroes),
            "termination_reason": state.termination_reason,
            "social_metrics": dict(state.social_metrics),
        }

    def unlock_new(
        self,
        state: GameState,
        *,
        before: dict[str, Any] | None = None,
    ) -> tuple[float, list[dict[str, Any]]]:
        before = before or {}
        new_events: list[dict[str, Any]] = []
        unlocked = set(state.achievements_unlocked)
        for achievement in self.definitions_for(state):
            if achievement.id in unlocked:
                continue
            if not self._condition_met(achievement.condition, state, before):
                continue
            unlocked.add(achievement.id)
            event = {
                "id": achievement.id,
                "title": achievement.title,
                "layer": achievement.layer,
                "reward": max(0.0, achievement.reward),
                "round": state.round,
            }
            if achievement.description:
                event["description"] = achievement.description
            new_events.append(event)

        if not new_events:
            return 0.0, []

        state.achievements_unlocked.update(event["id"] for event in new_events)
        state.achievement_events.extend(new_events)
        reward = sum(max(0.0, float(event["reward"])) for event in new_events)
        state.achievement_reward += reward
        state.event_log.append(
            "Achievements unlocked: " + ", ".join(event["title"] for event in new_events) + "."
        )
        return reward, new_events

    def _condition_met(
        self, condition: dict[str, Any], state: GameState, before: dict[str, Any]
    ) -> bool:
        condition_type = condition.get("type")
        if condition_type == "door_opened":
            return self._door_opened(state, before, condition.get("id"))
        if condition_type == "trap_revealed":
            return self._trap_revealed(state, before, condition.get("id"))
        if condition_type == "trap_disarmed":
            return self._trap_disarmed(state, before, condition.get("id"))
        if condition_type == "chest_opened":
            return self._chest_opened(state, before, condition.get("id"))
        if condition_type == "furniture_searched":
            return self._furniture_searched(
                state, before, condition.get("id"), condition.get("category")
            )
        if condition_type == "treasure_collected":
            return state.treasure_collected > int(before.get("treasure_collected", 0))
        if condition_type == "monster_defeated":
            return self._monster_defeated(
                state,
                before,
                condition.get("id"),
                condition.get("role"),
                condition.get("roles"),
            )
        if condition_type == "revived_monster_defeated":
            return self._revived_monster_defeated(state, before, condition.get("role"))
        if condition_type == "trace_kind_happened":
            return self._trace_kind_happened(
                state, before, condition.get("kind"), condition.get("kinds")
            )
        if condition_type == "all_trace_kinds_happened":
            return self._all_trace_kinds_happened(state, condition.get("kinds"))
        if condition_type == "spell_used":
            return self._spell_used(state, before, condition.get("spell"), condition.get("spells"))
        if condition_type == "objective_taken":
            return before.get("objective_carrier") is None and state.objective.carrier is not None
        if condition_type == "success":
            return state.done and state.winner == "heroes"
        if condition_type == "alert_below_success":
            return (
                state.done
                and state.winner == "heroes"
                and state.alert < int(condition.get("alert", condition.get("max", 1)))
            )
        if condition_type == "all_heroes_survive_success":
            return (
                state.done
                and state.winner == "heroes"
                and len(state.living_heroes()) == len(state.heroes)
            )
        if condition_type == "extracted_heroes_at_least":
            return len(state.extracted_heroes) >= int(condition.get("count", 1))
        if condition_type == "termination_reason":
            return state.termination_reason == str(condition.get("reason"))
        if condition_type == "social_metric_at_least":
            value = state.social_metrics.get(str(condition.get("metric", "")), 0)
            if isinstance(value, dict):
                total = sum(int(item) for item in value.values())
            else:
                total = int(value)
            return total >= int(condition.get("count", 1))
        if condition_type == "social_metric_at_least_success":
            value = state.social_metrics.get(str(condition.get("metric", "")), 0)
            if isinstance(value, dict):
                total = sum(int(item) for item in value.values())
            else:
                total = int(value)
            return (
                state.done and state.winner == "heroes" and total >= int(condition.get("count", 1))
            )
        if condition_type == "social_metric_at_most_success":
            value = state.social_metrics.get(str(condition.get("metric", "")), 0)
            if isinstance(value, dict):
                total = sum(int(item) for item in value.values())
            else:
                total = int(value)
            return (
                state.done and state.winner == "heroes" and total <= int(condition.get("count", 0))
            )
        if condition_type == "messages_sent_at_least":
            if len(state.heroes) < int(condition.get("min_heroes", 1)):
                return False
            return len(state.party_messages) >= int(condition.get("count", 1))
        if condition_type == "known_floor_tiles_at_least":
            return self._known_floor_tiles(state) >= int(condition.get("count", 1))
        if condition_type == "rooms_explored_at_least":
            return self._rooms_explored(state) >= int(condition.get("count", 1))
        if condition_type == "round_at_most_success":
            return (
                state.done
                and state.winner == "heroes"
                and state.round <= int(condition.get("round", 999))
            )
        if condition_type == "inventory_contains":
            item = condition.get("item")
            return any(item in hero.inventory for hero in state.heroes.values())
        return False

    def _door_opened(self, state: GameState, before: dict[str, Any], door_id: Any = None) -> bool:
        door_ids = [str(door_id)] if door_id else list(state.doors)
        before_doors = before.get("doors", {})
        return any(
            before_doors.get(did, {}).get("state") == "closed" and state.doors[did].state == "open"
            for did in door_ids
            if did in state.doors
        )

    def _trap_revealed(self, state: GameState, before: dict[str, Any], trap_id: Any = None) -> bool:
        trap_ids = [str(trap_id)] if trap_id else list(state.traps)
        before_traps = before.get("traps", {})
        return any(
            not before_traps.get(tid, {}).get("revealed", False) and state.traps[tid].revealed
            for tid in trap_ids
            if tid in state.traps
        )

    def _trap_disarmed(self, state: GameState, before: dict[str, Any], trap_id: Any = None) -> bool:
        trap_ids = [str(trap_id)] if trap_id else list(state.traps)
        before_traps = before.get("traps", {})
        return any(
            before_traps.get(tid, {}).get("armed", False) and not state.traps[tid].armed
            for tid in trap_ids
            if tid in state.traps
        )

    def _chest_opened(self, state: GameState, before: dict[str, Any], chest_id: Any = None) -> bool:
        chest_ids = [str(chest_id)] if chest_id else list(state.chests)
        before_chests = before.get("chests", {})
        return any(
            not before_chests.get(cid, {}).get("opened", False) and state.chests[cid].opened
            for cid in chest_ids
            if cid in state.chests
        )

    def _furniture_searched(
        self,
        state: GameState,
        before: dict[str, Any],
        furniture_id: Any = None,
        category: Any = None,
    ) -> bool:
        furniture_ids = [str(furniture_id)] if furniture_id else list(state.furniture)
        before_furniture = before.get("furniture", {})
        return any(
            not before_furniture.get(fid, {}).get("searched", False)
            and state.furniture[fid].searched
            and (category is None or state.furniture[fid].category == category)
            for fid in furniture_ids
            if fid in state.furniture
        )

    def _monster_defeated(
        self,
        state: GameState,
        before: dict[str, Any],
        monster_id: Any = None,
        role: Any = None,
        roles: Any = None,
    ) -> bool:
        before_monsters = before.get("monsters", {})
        monster_ids = [str(monster_id)] if monster_id else list(state.monsters)
        role_set = {str(item) for item in roles} if isinstance(roles, list) else None
        return any(
            before_monsters.get(mid, {}).get("alive", False)
            and not state.monsters[mid].alive
            and (role is None or state.monsters[mid].role == role)
            and (role_set is None or state.monsters[mid].role in role_set)
            for mid in monster_ids
            if mid in state.monsters
        )

    def _revived_monster_defeated(
        self, state: GameState, before: dict[str, Any], role: Any = None
    ) -> bool:
        before_monsters = before.get("monsters", {})
        return any(
            before_monsters.get(monster_id, {}).get("alive", False)
            and "revived" in before_monsters.get(monster_id, {}).get("status", [])
            and not monster.alive
            and (role is None or monster.role == role)
            for monster_id, monster in state.monsters.items()
        )

    def _trace_kind_happened(
        self,
        state: GameState,
        before: dict[str, Any],
        kind: Any = None,
        kinds: Any = None,
    ) -> bool:
        kind_set = {str(kind)} if kind else set()
        if isinstance(kinds, list):
            kind_set.update(str(item) for item in kinds)
        if not kind_set:
            return False
        before_counts = before.get("trace_kind_counts", {})
        after_counts = self._trace_kind_counts(state)
        return any(after_counts.get(item, 0) > before_counts.get(item, 0) for item in kind_set)

    def _all_trace_kinds_happened(self, state: GameState, kinds: Any = None) -> bool:
        if not isinstance(kinds, list) or not kinds:
            return False
        counts = self._trace_kind_counts(state)
        return all(counts.get(str(kind), 0) > 0 for kind in kinds)

    def _spell_used(
        self, state: GameState, before: dict[str, Any], spell: Any = None, spells: Any = None
    ) -> bool:
        spell_set = {str(spell)} if spell else set()
        if isinstance(spells, list):
            spell_set.update(str(item) for item in spells)
        before_count = int(before.get("trace_kind_counts", {}).get("spell_used", 0))
        seen = 0
        for event in state.trace:
            if event.get("kind") != "spell_used":
                continue
            seen += 1
            if seen <= before_count:
                continue
            if not spell_set or str(event.get("spell")) in spell_set:
                return True
        return False

    def _trace_kind_counts(self, state: GameState) -> dict[str, int]:
        counts: dict[str, int] = {}
        for event in state.trace:
            kind = event.get("kind") if isinstance(event, dict) else None
            if kind:
                counts[str(kind)] = counts.get(str(kind), 0) + 1
        return counts

    def _known_floor_tiles(self, state: GameState) -> int:
        return len([pos for pos in state.known_tiles if state.terrain[pos[1]][pos[0]] == "."])

    def _rooms_explored(self, state: GameState) -> int:
        return sum(1 for room in self._room_regions(state) if room & state.known_tiles)

    def _room_regions(self, state: GameState) -> list[set[Pos]]:
        blocked_doors = {door.pos for door in state.doors.values()}
        floor = {
            (x, y)
            for y, row in enumerate(state.terrain)
            for x, cell in enumerate(row)
            if cell == "." and (x, y) not in blocked_doors
        }
        regions: list[set[Pos]] = []
        while floor:
            start = floor.pop()
            region = {start}
            stack = [start]
            while stack:
                pos = stack.pop()
                x, y = pos
                for nxt in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
                    if nxt not in floor:
                        continue
                    floor.remove(nxt)
                    region.add(nxt)
                    stack.append(nxt)
            regions.append(region)
        return regions


def achievement_from_quest(quest_id: str, data: dict[str, Any]) -> list[Achievement]:
    achievements: list[Achievement] = []
    for raw in data.get("achievements", []):
        achievement_id = str(raw["id"])
        if "." not in achievement_id:
            achievement_id = f"{quest_id}.{achievement_id}"
        achievements.append(
            Achievement(
                id=achievement_id,
                title=str(
                    raw.get("title") or achievement_id.rsplit(".", 1)[-1].replace("_", " ").title()
                ),
                layer="quest",
                reward=float(raw.get("reward", 0.1)),
                condition=dict(raw.get("condition", {})),
                description=str(raw.get("description", "")),
            )
        )
    return achievements
