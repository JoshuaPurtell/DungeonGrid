"""GridEngine: maps, visibility, hidden information, rendering."""

from __future__ import annotations

import json
import random
from collections import deque
from importlib import resources
from pathlib import Path
from typing import Any, Iterable, Optional

from .data import (
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
    GameState,
    Objective,
    Pos,
    Trap,
)


class GridEngine:
    """Loads quests, parses ASCII grids, computes visibility, and renders maps."""

    def __init__(self, quest_dir: str | Path | None = None) -> None:
        self.quest_dir = Path(quest_dir) if quest_dir else None

    def available_quests(self) -> list[str]:
        if self.quest_dir:
            return sorted(p.stem for p in self.quest_dir.glob("*.json"))
        quest_pkg = resources.files("dungeongrid.quests")
        return sorted(p.name[:-5] for p in quest_pkg.iterdir() if p.name.endswith(".json"))

    def load_quest_data(self, quest_id: str) -> dict[str, Any]:
        filename = f"{quest_id}.json"
        if self.quest_dir:
            path = self.quest_dir / filename
            if not path.exists():
                raise FileNotFoundError(f"Quest not found: {quest_id}")
            return json.loads(path.read_text(encoding="utf-8"))
        try:
            text = (
                resources.files("dungeongrid.quests")
                .joinpath(filename)
                .read_text(encoding="utf-8")
            )
            return json.loads(text)
        except FileNotFoundError as exc:
            raise FileNotFoundError(f"Quest not found: {quest_id}") from exc

    def new_state(self, quest_id: str = "lantern_crypt", num_heroes: int = 4, seed: int | None = None) -> GameState:
        rng = random.Random(seed)
        data = self.load_quest_data(quest_id)
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
                    monsters[monster_id] = Entity(
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
                    )
                else:
                    raise ValueError(f"Unsupported map glyph {char!r} at {pos}")
            terrain.append(row)

        if randomized_chests:
            options = list(randomized_chests.get("contents", []))
            chest_ids = list(chests)
            rng.shuffle(options)
            for chest_id, contents in zip(chest_ids, options):
                chests[chest_id].contents = contents

        if entry is None:
            raise ValueError(f"Quest {quest_id!r} needs an entry tile 'E'")
        if objective_pos is None:
            objective_pos = tuple(data["objective"].get("start_pos", entry))  # type: ignore[assignment]

        roles = list(data.get("recommended_heroes", ["barbarian", "wizard", "elf", "dwarf"]))[
            :num_heroes
        ]
        legacy_roles = {
            "vanguard": "barbarian",
            "adept": "wizard",
            "scout": "elf",
            "healer": "dwarf",
        }
        roles = [legacy_roles.get(role, role) for role in roles]
        hero_starts_raw = data.get("hero_starts")
        if hero_starts_raw:
            starts = [tuple(p) for p in hero_starts_raw[:num_heroes]]
        else:
            starts = self._adjacent_start_positions(entry, terrain, num_heroes)
        heroes: dict[str, Entity] = {}
        for idx, role in enumerate(roles, start=1):
            spec = HERO_ARCHETYPES[role]
            hero_id = f"hero_{idx}"
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
            )

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
            scripts=data.get("scripts", {}),
            hero_order=list(heroes),
            ap_remaining={hero_id: 3 for hero_id in heroes},
            torch=int(data.get("torch", 20)),
        )
        state.known_tiles.update(self.visible_tiles(state, agent_id="party"))
        return state

    def _adjacent_start_positions(self, entry: Pos, terrain: list[list[str]], num_heroes: int) -> list[Pos]:
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
        if door and door.secret and not door.discovered and for_heroes:
            return True
        return False

    def is_transparent(self, state: GameState, pos: Pos) -> bool:
        if self.is_wall(state, pos):
            return False
        door = state.door_at(pos)
        return not (door and door.state == "closed")

    def is_walkable(self, state: GameState, pos: Pos, ignore_entities: bool = False, for_heroes: bool = True) -> bool:
        if self.is_wall(state, pos, for_heroes=for_heroes):
            return False
        door = state.door_at(pos)
        if door and door.state == "closed":
            return False
        if not ignore_entities and state.entity_at(pos) is not None:
            return False
        return True

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

    def find_path(self, state: GameState, start: Pos, goal: Pos, ignore_entities: bool = True) -> list[Pos]:
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

    def render_ascii(self, state: GameState, agent_id: str | None = None, known_only: bool = True) -> str:
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
            return MONSTER_RENDER_GLYPHS.get(ent.role, "m")
        if state.objective.pos == pos and state.objective.carrier is None and not state.objective.recovered:
            return "I"
        chest = state.chest_at(pos)
        if chest and not chest.opened:
            return "C"
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
                if entity.team == "dungeon" and agent_id != "warden" and entity.pos not in visible:
                    continue
                result.append(entity.to_dict())
        return result

    def visible_objects(self, state: GameState, agent_id: str) -> list[dict[str, Any]]:
        visible = self.visible_tiles(state, agent_id)
        objs: list[dict[str, Any]] = []
        for door in state.doors.values():
            if door.pos in visible and (agent_id == "warden" or not door.secret or door.discovered):
                objs.append({"type": "door", **door.to_dict()})
        for chest in state.chests.values():
            if chest.pos in visible and not chest.opened:
                data = {"type": "chest", "id": chest.id, "pos": list(chest.pos), "opened": chest.opened}
                if agent_id == "warden":
                    data["contents"] = chest.contents
                objs.append(data)
        for trap in state.traps.values():
            if trap.pos in visible and (agent_id == "warden" or trap.revealed):
                objs.append({"type": "trap", **trap.to_dict()})
        if state.objective.pos and state.objective.pos in visible and state.objective.carrier is None:
            objs.append({"type": "objective", **state.objective.to_dict()})
        return objs
