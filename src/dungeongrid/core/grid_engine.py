"""GridEngine: maps, visibility, hidden information, rendering."""

from __future__ import annotations

import json
import random
from collections import deque
from collections.abc import Iterable
from importlib import resources
from pathlib import Path
from typing import Any

from ..achievements import achievement_from_quest
from .data import (
    CLASSIC_DYNAMIC_RULESET,
    DEFAULT_CLASSIC_TREASURE_DECK,
    DIRECTIONS,
    HERO_ARCHETYPES,
    HERO_GLYPHS,
    MONSTER_GLYPHS,
    MONSTER_RENDER_GLYPHS,
    MONSTER_TYPES,
    ROLE_GLYPHS,
    Chest,
    Door,
    Entity,
    Furniture,
    GameState,
    Objective,
    Pos,
    Trap,
    default_per_hero_stats,
)


class GridEngine:
    """Loads quests, parses ASCII grids, computes visibility, and renders maps."""

    def __init__(self, quest_dir: str | Path | None = None) -> None:
        self.quest_dir = Path(quest_dir) if quest_dir else None

    def available_quests(self) -> list[str]:
        if self.quest_dir:
            return sorted(p.name for p in self.quest_dir.iterdir() if (p / "quest.json").exists())
        dungeon_pkg = resources.files("dungeongrid.dungeons")
        return sorted(
            p.name
            for p in dungeon_pkg.iterdir()
            if p.is_dir() and p.joinpath("quest.json").is_file()
        )

    def load_quest_data(self, quest_id: str) -> dict[str, Any]:
        if self.quest_dir:
            path = self.quest_dir / quest_id / "quest.json"
            if not path.exists():
                raise FileNotFoundError(f"Quest not found: {quest_id}")
            return json.loads(path.read_text(encoding="utf-8"))
        try:
            text = (
                resources.files("dungeongrid.dungeons")
                .joinpath(quest_id, "quest.json")
                .read_text(encoding="utf-8")
            )
            return json.loads(text)
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"Quest not found: {quest_id}") from exc

    def new_state(
        self,
        quest_id: str = "lantern_crypt",
        num_heroes: int = 4,
        seed: int | None = None,
        ruleset: str | dict[str, Any] | None = None,
        hero_roles: list[str] | None = None,
    ) -> GameState:
        rng = random.Random(seed)
        data = self.load_quest_data(quest_id)
        resolved_ruleset = self._resolve_ruleset(data, ruleset)
        ascii_map = data["map"]["ascii"]
        lines = [line.rstrip("\n") for line in ascii_map.strip("\n").splitlines()]
        if not lines:
            raise ValueError("Quest map cannot be empty")
        width = len(lines[0])
        if any(len(line) != width for line in lines):
            raise ValueError(f"Quest map {quest_id!r} is not rectangular")

        terrain: list[list[str]] = []
        doors: dict[str, Door] = {}
        traps: dict[str, Trap] = {}
        chests: dict[str, Chest] = {}
        monsters: dict[str, Entity] = {}
        entry: Pos | None = None
        objective_pos: Pos | None = None
        door_count = secret_count = trap_count = chest_count = 0
        monster_counts: dict[str, int] = {}

        chest_contents = data.get("chest_contents", {})
        randomized_chests = data.get("randomized_chests")
        monster_activation = data.get("monster_activation", {})
        default_activation = str(monster_activation.get("default", "dormant"))
        default_wake_on = str(monster_activation.get("wake_on", "room_revealed"))

        for y, line in enumerate(lines):
            row: list[str] = []
            for x, char in enumerate(line):
                pos = (x, y)
                if char == "#":
                    row.append("#")
                elif char in ".E":
                    row.append(".")
                    if char == "E":
                        entry = pos
                elif char == "D":
                    row.append(".")
                    door_count += 1
                    doors[f"door_{door_count}"] = Door(id=f"door_{door_count}", pos=pos)
                elif char == "S":
                    row.append(".")
                    secret_count += 1
                    doors[f"secret_{secret_count}"] = Door(
                        id=f"secret_{secret_count}", pos=pos, secret=True, discovered=False
                    )
                elif char == "T":
                    row.append(".")
                    trap_count += 1
                    traps[f"trap_{trap_count}"] = Trap(id=f"trap_{trap_count}", pos=pos)
                elif char == "C":
                    row.append(".")
                    chest_count += 1
                    chest_id = f"chest_{chest_count}"
                    contents = chest_contents.get(chest_id, "coin_cache")
                    chests[chest_id] = Chest(id=chest_id, pos=pos, contents=contents)
                elif char == "I":
                    row.append(".")
                    objective_pos = pos
                elif char in MONSTER_GLYPHS:
                    row.append(".")
                    role = MONSTER_GLYPHS[char]
                    monster_counts[role] = monster_counts.get(role, 0) + 1
                    monster_id = f"{role}_{monster_counts[role]}"
                    spec = MONSTER_TYPES[role]
                    monster = Entity(
                        id=monster_id,
                        team="dungeon",
                        role=role,
                        hp=spec["hp"],
                        max_hp=spec["hp"],
                        attack=spec["attack"],
                        guard=spec["guard"],
                        speed=spec["speed"],
                        behavior=spec["behavior"],
                        pos=pos,
                        room_id=self.room_id_at(data.get("rooms", {}), pos),
                        sight_range=int(spec.get("sight_range", 6)),
                        activation=str(spec.get("activation", default_activation)),
                        wake_on=str(spec.get("wake_on", default_wake_on)),
                        equipment={key: spec[key] for key in ("attack_range",) if key in spec},
                    )
                    self._apply_monster_override(monster, data.get("monster_overrides", {}))
                    self._apply_boss_config(monster, data.get("bosses", {}))
                    monsters[monster_id] = monster
                else:
                    raise ValueError(f"Unsupported map glyph {char!r} at {pos}")
            terrain.append(row)

        if randomized_chests:
            options = list(randomized_chests.get("contents", []))
            chest_ids = list(chests)
            rng.shuffle(options)
            for chest_id, contents in zip(chest_ids, options, strict=False):
                chests[chest_id].contents = contents

        if entry is None:
            raise ValueError(f"Quest {quest_id!r} needs an entry tile 'E'")
        if objective_pos is None:
            objective_pos = tuple(data["objective"].get("start_pos", entry))  # type: ignore[assignment]

        roles = self._select_roles(
            data,
            num_heroes=num_heroes,
            hero_roles=hero_roles,
            apply_requirements=bool(resolved_ruleset),
        )
        role_requirements = self._role_requirements(data, num_heroes)
        role_requirement_warnings = (
            [role for role in role_requirements if role not in roles]
            if not resolved_ruleset
            else []
        )
        hero_starts_raw = data.get("hero_starts")
        if hero_starts_raw:
            starts = [tuple(p) for p in hero_starts_raw[:num_heroes]]
        else:
            starts = self._adjacent_start_positions(entry, terrain, num_heroes)
        heroes: dict[str, Entity] = {}
        loadouts = data.get("hero_loadouts", {})
        for idx, role in enumerate(roles, start=1):
            spec = HERO_ARCHETYPES[role]
            hero_id = f"hero_{idx}"
            loadout = dict(loadouts.get(role, {}))
            inventory = list(loadout.get("items", []))
            equipment = dict(loadout)
            equipment.pop("items", None)
            heroes[hero_id] = Entity(
                id=hero_id,
                team="heroes",
                role=role,
                hp=spec["hp"],
                max_hp=spec["hp"],
                attack=spec["attack"],
                guard=spec["guard"],
                speed=spec["speed"],
                focus=spec["focus"],
                ability=spec["ability"],
                pos=starts[idx - 1],
                inventory=inventory,
                equipment=equipment,
            )

        furniture = {
            item["id"]: Furniture(
                id=item["id"],
                pos=tuple(item["pos"]),
                category=item.get("category", "furniture"),
                name=item.get("name", item["id"]),
                description=item.get("description", ""),
                deck=item.get("deck"),
                visible=bool(item.get("visible", True)),
                traits=list(item.get("traits", [])),
                hp=int(item.get("hp", item.get("max_hp", 1))),
                max_hp=int(item.get("max_hp", item.get("hp", 1))),
                destroyed=bool(item.get("destroyed", False)),
                destructible=bool(item.get("destructible", False)),
                blocks_movement=bool(item.get("blocks_movement", False)),
                blocks_los=bool(item.get("blocks_los", False)),
                cover=int(item.get("cover", 0)),
                searched_categories=set(item.get("searched_categories", [])),
                search_effects=dict(item.get("search_effects", {})),
                break_effect=item.get("break_effect"),
            )
            for item in data.get("furniture", [])
        }
        decks = {
            deck_id: [dict(card) for card in cards]
            for deck_id, cards in data.get("decks", {}).items()
        }
        if (
            resolved_ruleset.get("treasure_risk", {}).get("enabled")
            and resolved_ruleset.get("treasure_risk", {}).get("default_treasure_deck", True)
            and "treasure" not in decks
        ):
            decks["treasure"] = [dict(card) for card in DEFAULT_CLASSIC_TREASURE_DECK]
        objective = Objective(
            id=data["objective"].get("item_id", "objective_item"),
            pos=objective_pos,
            fragile=bool(data["objective"].get("fragile", False)),
        )
        state = GameState(
            quest_id=quest_id,
            title=data.get("title", quest_id),
            difficulty=data.get("difficulty", "starter"),
            width=width,
            height=len(lines),
            terrain=terrain,
            entry=entry,
            escape_tile=tuple(data["objective"].get("escape_tile", entry)),
            objective_type=data["objective"].get("type", "retrieve_and_escape"),
            objective=objective,
            heroes=heroes,
            monsters=monsters,
            doors=doors,
            traps=traps,
            chests=chests,
            furniture=furniture,
            rooms=dict(data.get("rooms", {})),
            decks=decks,
            discards={deck_id: [] for deck_id in decks},
            hero_loadouts=loadouts,
            scripts={
                **data.get("scripts", {}),
                "mechanics": dict(data.get("mechanics", {})),
                "metadata": dict(data.get("metadata", {})),
                "deck_policies": dict(data.get("deck_policies", {})),
                "role_gates": list(data.get("role_gates", [])),
                "role_requirements": {
                    "required_roles": role_requirements,
                    "mode": "hard" if resolved_ruleset else "soft",
                    "warnings": role_requirement_warnings,
                },
            },
            ruleset=resolved_ruleset,
            quest_achievement_defs=achievement_from_quest(quest_id, data),
            hero_order=list(heroes),
            ap_remaining={hero_id: 3 for hero_id in heroes},
            movement_remaining={hero_id: 0 for hero_id in heroes},
            movement_rolls={hero_id: 0 for hero_id in heroes},
            major_action_used={hero_id: False for hero_id in heroes},
            hero_treasure={hero_id: 0 for hero_id in heroes},
            per_hero_stats={
                hero_id: default_per_hero_stats(hero) for hero_id, hero in heroes.items()
            },
            social_metrics=self._initial_social_metrics(heroes),
            torch=int(data.get("torch", 20)),
        )
        if role_requirement_warnings:
            state.event_log.append(
                "Role warning: this dungeon favors "
                f"{role_requirement_warnings}, but default/AP mode keeps the run playable."
            )
        state.known_tiles.update(self.visible_tiles(state, agent_id="party"))
        self.update_revealed_rooms(state, reason="initial_visibility")
        return state

    def _resolve_ruleset(
        self, data: dict[str, Any], ruleset: str | dict[str, Any] | None
    ) -> dict[str, Any]:
        quest_rules = dict(data.get("ruleset", {}))
        if ruleset is None:
            return {}
        if ruleset == "classic_dynamic":
            base = self._deep_merge({}, CLASSIC_DYNAMIC_RULESET)
        elif isinstance(ruleset, dict):
            base = self._deep_merge({}, ruleset)
        else:
            base = {}
        return self._deep_merge(base, quest_rules)

    def _deep_merge(self, base: dict[str, Any], update: dict[str, Any]) -> dict[str, Any]:
        merged = dict(base)
        for key, value in update.items():
            if isinstance(value, dict) and isinstance(merged.get(key), dict):
                merged[key] = self._deep_merge(dict(merged[key]), value)
            else:
                merged[key] = value
        return merged

    def _select_roles(
        self,
        data: dict[str, Any],
        *,
        num_heroes: int,
        hero_roles: list[str] | None,
        apply_requirements: bool,
    ) -> list[str]:
        if hero_roles is not None:
            roles = [str(role) for role in hero_roles]
            if len(roles) != num_heroes:
                raise ValueError("hero_roles length must match num_heroes")
        else:
            recommended = [
                str(role)
                for role in data.get("recommended_heroes", ["barbarian", "wizard", "elf", "dwarf"])
            ]
            required = self._role_requirements(data, num_heroes) if apply_requirements else []
            roles = []
            for role in [*required, *recommended]:
                if role not in roles:
                    roles.append(role)
                if len(roles) == num_heroes:
                    break
        self._validate_roles(data, roles, num_heroes, apply_requirements=apply_requirements)
        return roles[:num_heroes]

    def _validate_roles(
        self, data: dict[str, Any], roles: list[str], num_heroes: int, *, apply_requirements: bool
    ) -> None:
        unknown = [role for role in roles if role not in HERO_ARCHETYPES]
        if unknown:
            raise ValueError(f"Unknown hero roles: {unknown}")
        if not apply_requirements:
            return
        required = self._role_requirements(data, num_heroes)
        missing = [role for role in required if role not in roles]
        if missing:
            raise ValueError(f"Quest requires roles for {num_heroes} heroes: {missing}")

    def _role_requirements(self, data: dict[str, Any], num_heroes: int) -> list[str]:
        explicit = [
            str(role)
            for role in data.get("role_selection", {})
            .get("required_roles_by_party_size", {})
            .get(str(num_heroes), [])
        ]
        if explicit:
            return explicit
        metadata = data.get("metadata", {})
        if not metadata.get("requires_specialist"):
            return []
        for role, affordances in metadata.get("role_affordances", {}).items():
            if any("specialist" in str(affordance) for affordance in affordances):
                return [str(role)]
        for role, loadout in data.get("hero_loadouts", {}).items():
            if "specialist" in str(loadout.get("combat_role", "")):
                return [str(role)]
        return ["dwarf"]

    def _initial_social_metrics(self, heroes: dict[str, Entity]) -> dict[str, Any]:
        return {
            "treasure_searches": {hero_id: 0 for hero_id in heroes},
            "bad_treasure_draws": {hero_id: 0 for hero_id in heroes},
            "wanderers_spawned_by_greed": 0,
            "items_given": 0,
            "objective_passes": 0,
            "rescue_actions": 0,
            "split_party_rounds": 0,
            "doorway_hold_turns": 0,
            "body_blocked_ally_escape": 0,
            "healing_items_given": 0,
            "potions_hoarded_while_ally_critical": 0,
            "specialist_actions": {},
        }

    def room_id_at(self, rooms: dict[str, Any], pos: Pos) -> str | None:
        x, y = pos
        for room_id, room in rooms.items():
            rect = room.get("rect") if isinstance(room, dict) else None
            if not isinstance(rect, list) or len(rect) != 4:
                continue
            x1, y1, x2, y2 = [int(v) for v in rect]
            if x1 <= x <= x2 and y1 <= y <= y2:
                return str(room_id)
        return None

    def update_revealed_rooms(
        self, state: GameState, reason: str, opener_id: str | None = None
    ) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        visible = self.visible_tiles(state, "party")
        for room_id, room in state.rooms.items():
            if room_id in state.revealed_rooms or not isinstance(room, dict):
                continue
            rect = room.get("rect")
            if not isinstance(rect, list) or len(rect) != 4:
                continue
            x1, y1, x2, y2 = [int(v) for v in rect]
            room_tiles = {(x, y) for y in range(y1, y2 + 1) for x in range(x1, x2 + 1)}
            if not (room_tiles & visible):
                continue
            state.revealed_rooms.add(str(room_id))
            event = {
                "kind": "room_revealed",
                "room_id": str(room_id),
                "room_name": room.get("name", room_id),
                "reason": reason,
                "opener_id": opener_id,
            }
            state.trace.append(event)
            state.event_log.append(f"Room revealed: {event['room_name']}.")
            events.append(event)
            events.extend(self.activate_room_monsters(state, str(room_id), reason=reason))
        return events

    def activate_room_monsters(
        self, state: GameState, room_id: str, reason: str
    ) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for monster in state.monsters.values():
            if not monster.alive or monster.room_id != room_id or monster.activation != "dormant":
                continue
            if monster.wake_on in {
                "line_of_sight",
                "visible",
                "sighted",
            } and not self._monster_seen_by_party(state, monster):
                continue
            if monster.wake_on in {"alert", "alarm"} and state.alert <= 0:
                continue
            monster.activation = "alert"
            event = {
                "kind": "monster_activated",
                "monster_id": monster.id,
                "role": monster.role,
                "room_id": room_id,
                "reason": reason,
            }
            state.trace.append(event)
            state.event_log.append(f"{monster.role} wakes in {room_id}.")
            events.append(event)
        return events

    def update_monster_awareness(self, state: GameState, reason: str) -> list[dict[str, Any]]:
        events: list[dict[str, Any]] = []
        for monster in state.monsters.values():
            if not monster.alive or monster.activation != "dormant":
                continue
            should_wake = False
            if monster.wake_on in {"line_of_sight", "visible", "sighted"}:
                should_wake = self._monster_seen_by_party(state, monster)
            elif monster.wake_on in {"alert", "alarm"}:
                should_wake = state.alert > 0
            elif monster.wake_on in {"objective_taken", "objective"}:
                should_wake = bool(state.objective.carrier)
            if not should_wake:
                continue
            monster.activation = "alert"
            event = {
                "kind": "monster_activated",
                "monster_id": monster.id,
                "role": monster.role,
                "room_id": monster.room_id,
                "reason": reason,
                "wake_on": monster.wake_on,
            }
            state.trace.append(event)
            state.event_log.append(f"{monster.role} notices the party.")
            events.append(event)
        return events

    def _monster_seen_by_party(self, state: GameState, monster: Entity) -> bool:
        for hero in state.heroes.values():
            if not hero.alive:
                continue
            if self.manhattan(hero.pos, monster.pos) > monster.sight_range:
                continue
            if self.line_clear(state, hero.pos, monster.pos):
                return True
        return False

    def _apply_monster_override(self, monster: Entity, overrides: Any) -> None:
        if not isinstance(overrides, dict):
            return
        raw = overrides.get(monster.id) or overrides.get(monster.role)
        if not isinstance(raw, dict):
            return
        for attr in (
            "hp",
            "max_hp",
            "attack",
            "guard",
            "speed",
            "behavior",
            "activation",
            "wake_on",
            "sight_range",
        ):
            if attr not in raw:
                continue
            value = raw[attr]
            if attr in {"hp", "max_hp", "attack", "guard", "speed", "sight_range"}:
                value = int(value)
            setattr(monster, attr, value)
        if "hp" in raw and "max_hp" not in raw:
            monster.max_hp = int(raw["hp"])
        if isinstance(raw.get("status"), list):
            monster.status.extend(
                str(item) for item in raw["status"] if str(item) not in monster.status
            )
        if isinstance(raw.get("equipment"), dict):
            monster.equipment.update(raw["equipment"])

    def _apply_boss_config(self, monster: Entity, bosses: Any) -> None:
        if not isinstance(bosses, dict):
            return
        raw = bosses.get(monster.id) or bosses.get(monster.role)
        if not isinstance(raw, dict):
            return
        monster.equipment["boss"] = True
        if raw.get("name"):
            monster.equipment["boss_name"] = str(raw["name"])
        for key in (
            "public_summary",
            "counterplay_hint",
            "defeat_reward",
            "defeat_description",
            "on_defeated",
        ):
            if key in raw:
                monster.equipment[key] = raw[key]
        if isinstance(raw.get("damage_gate"), dict):
            gate = dict(raw["damage_gate"])
            monster.equipment["damage_gate"] = gate
            if gate.get("counter_flag"):
                monster.equipment["counter_flag"] = gate["counter_flag"]
            if gate.get("max_damage_without_counter") is not None:
                monster.equipment["max_damage_without_counter"] = gate["max_damage_without_counter"]
        if isinstance(raw.get("phases"), list):
            monster.equipment["phases"] = [
                dict(phase) for phase in raw["phases"] if isinstance(phase, dict)
            ]

    def _adjacent_start_positions(
        self, entry: Pos, terrain: list[list[str]], num_heroes: int
    ) -> list[Pos]:
        width, height = len(terrain[0]), len(terrain)
        starts = [entry]
        q: deque[Pos] = deque([entry])
        seen = {entry}
        while q and len(starts) < num_heroes:
            x, y = q.popleft()
            for dx, dy in DIRECTIONS.values():
                nxt = (x + dx, y + dy)
                if nxt in seen:
                    continue
                seen.add(nxt)
                nx, ny = nxt
                if 0 <= nx < width and 0 <= ny < height and terrain[ny][nx] == ".":
                    starts.append(nxt)
                    q.append(nxt)
        if len(starts) < num_heroes:
            raise ValueError("Map does not have enough free start tiles for heroes")
        return starts[:num_heroes]

    def in_bounds(self, state: GameState, pos: Pos) -> bool:
        x, y = pos
        return 0 <= x < state.width and 0 <= y < state.height

    def terrain_at(self, state: GameState, pos: Pos) -> str:
        x, y = pos
        if not self.in_bounds(state, pos):
            return "#"
        return state.terrain[y][x]

    def is_wall(self, state: GameState, pos: Pos, for_heroes: bool = True) -> bool:
        if not self.in_bounds(state, pos):
            return True
        if self.terrain_at(state, pos) == "#":
            return True
        door = state.door_at(pos)
        return bool(door and door.secret and not door.discovered and for_heroes)

    def is_transparent(self, state: GameState, pos: Pos) -> bool:
        if self.is_wall(state, pos):
            return False
        furniture = self.furniture_at(state, pos)
        if furniture and not furniture.destroyed and furniture.blocks_los:
            return False
        door = state.door_at(pos)
        return not (door and door.state == "closed")

    def is_walkable(
        self, state: GameState, pos: Pos, ignore_entities: bool = False, for_heroes: bool = True
    ) -> bool:
        if self.is_wall(state, pos, for_heroes=for_heroes):
            return False
        door = state.door_at(pos)
        if door and door.state == "closed":
            return False
        furniture = self.furniture_at(state, pos)
        if furniture and not furniture.destroyed and furniture.blocks_movement:
            return False
        return not (not ignore_entities and state.entity_at(pos) is not None)

    def furniture_at(self, state: GameState, pos: Pos) -> Furniture | None:
        return next(
            (item for item in state.furniture.values() if item.pos == pos and item.visible), None
        )

    def neighbors(self, state: GameState, pos: Pos, ignore_entities: bool = True) -> Iterable[Pos]:
        x, y = pos
        for dx, dy in DIRECTIONS.values():
            nxt = (x + dx, y + dy)
            if self.is_walkable(state, nxt, ignore_entities=ignore_entities, for_heroes=False):
                yield nxt

    def visible_tiles(self, state: GameState, agent_id: str, radius: int | None = None) -> set[Pos]:
        if agent_id == "warden":
            return {(x, y) for y in range(state.height) for x in range(state.width)}
        radius = radius if radius is not None else max(3, min(6, state.torch // 4 + 2))
        origins: list[Pos]
        if agent_id in state.heroes:
            hero = state.heroes[agent_id]
            origins = [hero.pos] if hero.alive else []
        else:
            origins = [h.pos for h in state.heroes.values() if h.alive]
        visible: set[Pos] = set()
        for origin in origins:
            q: deque[tuple[Pos, int]] = deque([(origin, 0)])
            seen = {origin}
            while q:
                pos, dist = q.popleft()
                visible.add(pos)
                if dist >= radius:
                    continue
                if dist > 0 and not self.is_transparent(state, pos):
                    continue
                x, y = pos
                for dx, dy in DIRECTIONS.values():
                    nxt = (x + dx, y + dy)
                    if nxt in seen or not self.in_bounds(state, nxt):
                        continue
                    if self.is_wall(state, nxt):
                        if state.door_at(nxt) is not None:
                            visible.add(nxt)
                        continue
                    seen.add(nxt)
                    q.append((nxt, dist + 1))
        return visible

    def update_known_tiles(self, state: GameState) -> None:
        state.known_tiles.update(self.visible_tiles(state, agent_id="party"))

    def adjacent_positions(self, pos: Pos) -> list[Pos]:
        x, y = pos
        return [(x + dx, y + dy) for dx, dy in DIRECTIONS.values()]

    def manhattan(self, a: Pos, b: Pos) -> int:
        return abs(a[0] - b[0]) + abs(a[1] - b[1])

    def find_path(
        self, state: GameState, start: Pos, goal: Pos, ignore_entities: bool = True
    ) -> list[Pos]:
        if start == goal:
            return [start]
        q: deque[Pos] = deque([start])
        parent: dict[Pos, Pos | None] = {start: None}
        while q:
            pos = q.popleft()
            for nxt in self.neighbors(state, pos, ignore_entities=ignore_entities):
                if nxt in parent:
                    continue
                parent[nxt] = pos
                if nxt == goal:
                    path = [goal]
                    cur = pos
                    while cur is not None:
                        path.append(cur)
                        cur = parent[cur]
                    return list(reversed(path))
                q.append(nxt)
        return []

    def line_clear(self, state: GameState, start: Pos, end: Pos) -> bool:
        if start[0] != end[0] and start[1] != end[1]:
            return False
        x, y = start
        dx = 0 if start[0] == end[0] else (1 if end[0] > start[0] else -1)
        dy = 0 if start[1] == end[1] else (1 if end[1] > start[1] else -1)
        while (x, y) != end:
            x += dx
            y += dy
            if (x, y) == end:
                break
            if not self.is_transparent(state, (x, y)):
                return False
        return True

    def render_ascii(
        self, state: GameState, agent_id: str | None = None, known_only: bool = True
    ) -> str:
        if agent_id == "warden" or known_only is False:
            visible = {(x, y) for y in range(state.height) for x in range(state.width)}
        else:
            visible = self.visible_tiles(state, agent_id or "party")
            state.known_tiles.update(visible)
        rows: list[str] = []
        for y in range(state.height):
            chars: list[str] = []
            for x in range(state.width):
                pos = (x, y)
                if agent_id != "warden" and known_only and pos not in state.known_tiles:
                    chars.append(" ")
                    continue
                if agent_id != "warden" and pos not in visible:
                    # Known but not currently visible.
                    base = "#" if self.terrain_at(state, pos) == "#" else "."
                    door = state.door_at(pos)
                    if door and (not door.secret or door.discovered):
                        base = "/" if door.state == "open" else "D"
                    chars.append(base.lower())
                    continue
                chars.append(self._glyph_at(state, pos, agent_id))
            rows.append("".join(chars))
        return "\n".join(rows)

    def _glyph_at(self, state: GameState, pos: Pos, agent_id: str | None = None) -> str:
        ent = state.entity_at(pos)
        if ent:
            if ent.team == "heroes":
                return HERO_GLYPHS.get(ent.id, ROLE_GLYPHS.get(ent.role, "@"))
            if agent_id != "warden" and ent.activation == "dormant":
                return "." if self.terrain_at(state, pos) == "." else "#"
            return MONSTER_RENDER_GLYPHS.get(ent.role, "m")
        if (
            state.objective.pos == pos
            and state.objective.carrier is None
            and not state.objective.recovered
        ):
            return "I"
        chest = state.chest_at(pos)
        if chest and not chest.opened:
            return "C"
        furniture = self.furniture_at(state, pos)
        if furniture and not furniture.destroyed:
            return {
                "armory": "A",
                "altar": "a",
                "signal": "d",
                "hazard": "v",
                "lore": "l",
                "supply": "s",
                "treasure": "$",
            }.get(furniture.category, "f")
        trap = state.trap_at(pos)
        if trap and trap.revealed and trap.armed:
            return "T"
        door = state.door_at(pos)
        if door:
            if door.secret and not door.discovered and agent_id != "warden":
                return "#"
            return "/" if door.state == "open" else "D"
        if pos == state.entry or pos == state.escape_tile:
            return "E"
        return "#" if self.terrain_at(state, pos) == "#" else "."

    def visible_entities(self, state: GameState, agent_id: str) -> list[dict[str, Any]]:
        visible = self.visible_tiles(state, agent_id)
        result: list[dict[str, Any]] = []
        for entity in state.all_entities().values():
            if entity.alive and entity.pos in visible:
                if (
                    entity.team == "dungeon"
                    and agent_id != "warden"
                    and entity.activation == "dormant"
                ):
                    continue
                if entity.team == "dungeon" and agent_id != "warden" and entity.pos not in visible:
                    continue
                data = entity.to_dict()
                if entity.team == "dungeon" and agent_id != "warden":
                    equipment = data.pop("equipment", {})
                    if isinstance(equipment, dict) and equipment.get("boss"):
                        data["boss"] = True
                        data["boss_name"] = equipment.get("boss_name", entity.role)
                        data["boss_phase"] = (equipment.get("triggered_phases") or ["base"])[-1]
                        if equipment.get("public_summary"):
                            data["boss_summary"] = equipment["public_summary"]
                        if equipment.get("counterplay_hint"):
                            data["boss_counterplay_hint"] = equipment["counterplay_hint"]
                result.append(data)
        return result

    def visible_objects(self, state: GameState, agent_id: str) -> list[dict[str, Any]]:
        visible = self.visible_tiles(state, agent_id)
        objs: list[dict[str, Any]] = []
        for door in state.doors.values():
            if door.pos in visible and (agent_id == "warden" or not door.secret or door.discovered):
                objs.append({"type": "door", **door.to_dict()})
        for chest in state.chests.values():
            if chest.pos in visible and not chest.opened:
                data = {
                    "type": "chest",
                    "id": chest.id,
                    "pos": list(chest.pos),
                    "opened": chest.opened,
                }
                if agent_id == "warden":
                    data["contents"] = chest.contents
                objs.append(data)
        for furniture in state.furniture.values():
            if furniture.visible and furniture.pos in visible and not furniture.destroyed:
                data = {"type": "furniture", **furniture.to_dict()}
                if agent_id != "warden":
                    data.pop("deck", None)
                    data.pop("search_effects", None)
                    data.pop("break_effect", None)
                objs.append(data)
        for trap in state.traps.values():
            if trap.pos in visible and (agent_id == "warden" or trap.revealed):
                objs.append({"type": "trap", **trap.to_dict()})
        if (
            state.objective.pos
            and state.objective.pos in visible
            and state.objective.carrier is None
        ):
            objs.append({"type": "objective", **state.objective.to_dict()})
        return objs
