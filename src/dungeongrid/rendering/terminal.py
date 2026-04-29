"""NetHack-style terminal renderer for DungeonGrid state replays."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any

CELL_W = 10
CELL_H = 18
PADDING = 14
TERM_COLS = 80
TERM_ROWS = 24
PANEL_W = 430
BG = (6, 8, 10)
PANEL_BG = (13, 17, 23)
FG = (224, 229, 236)
MESSAGE_FG = (114, 255, 145)
DIM = (40, 47, 58)
COLORS = {
    "#": (165, 170, 181),
    "-": (165, 170, 181),
    "|": (165, 170, 181),
    "+": (210, 153, 83),
    ".": (82, 220, 102),
    " ": (28, 32, 38),
    "D": (224, 166, 88),
    "/": (173, 216, 150),
    "T": (231, 92, 92),
    "^": (231, 92, 92),
    "C": (238, 198, 97),
    "A": (205, 211, 215),
    "a": (232, 166, 74),
    "d": (223, 164, 86),
    "v": (238, 97, 65),
    "l": (213, 190, 130),
    "s": (117, 201, 142),
    "$": (255, 220, 90),
    "f": (180, 155, 111),
    "%": (116, 92, 72),
    "I": (255, 215, 112),
    "E": (106, 192, 255),
    "@": (255, 255, 255),
    "B": (255, 117, 117),
    "W": (172, 132, 255),
    "E_HERO": (93, 220, 146),
    "D_HERO": (244, 190, 100),
    "g": (153, 211, 115),
    "b": (204, 210, 220),
    "k": (197, 126, 230),
    "r": (255, 120, 87),
    "w": (122, 207, 255),
}


def render_terminal_frame(
    state_json: dict[str, Any],
    events: dict[str, Any] | None = None,
    width_px: int | None = None,
):
    """Render a single DungeonGrid state as a PIL image.

    Pillow is imported lazily so plain DungeonGrid imports do not need the
    rendering extra.
    """

    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:  # pragma: no cover - depends on optional extra
        raise ImportError("Install dungeongrid[render] to render terminal frames.") from exc

    events = events or {}
    grid = _grid_from_state(state_json)
    width = width_px or (PADDING * 2 + TERM_COLS * CELL_W)
    height = PADDING * 2 + TERM_ROWS * CELL_H
    image = Image.new("RGB", (width, height), BG)
    draw = ImageDraw.Draw(image)
    font = _font(ImageFont, 16)

    _draw_terminal(draw, grid, state_json, events, PADDING, PADDING, font)
    return image


def render_terminal_gif(frames: list[dict[str, Any]], path: str | Path, fps: int = 2) -> Path:
    """Render replay frames to an animated GIF."""

    if not frames:
        raise ValueError("Cannot render an empty DungeonGrid replay.")
    try:
        import imageio.v2 as imageio
    except ImportError as exc:  # pragma: no cover - depends on optional extra
        raise ImportError("Install dungeongrid[render] to render GIF replays.") from exc

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    images = [
        render_terminal_frame(frame["state"], events=_frame_events(frame))
        for frame in frames
        if isinstance(frame.get("state"), dict)
    ]
    if not images:
        raise ValueError("DungeonGrid replay frames do not include state payloads.")
    duration = 1 / max(int(fps), 1)
    imageio.mimsave(path, images, duration=duration)
    return path


def render_terminal_html(
    frames: list[dict[str, Any]], path: str | Path, title: str | None = None
) -> Path:
    """Write a self-contained terminal-style HTML replay."""

    if not frames:
        raise ValueError("Cannot render an empty DungeonGrid replay.")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    title = title or _title_from_frames(frames)
    frame_html = "\n".join(_html_frame(frame, index) for index, frame in enumerate(frames))
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<style>
:root {{ color-scheme: dark; }}
body {{
  margin: 0;
  background: #05070a;
  color: #d8dee9;
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}}
header {{
  position: sticky;
  top: 0;
  z-index: 2;
  background: #0b0f16;
  border-bottom: 1px solid #263041;
  padding: 12px 18px;
}}
h1 {{ font-size: 18px; margin: 0; }}
.frames {{ padding: 18px; display: grid; gap: 18px; }}
.frame {{
  display: grid;
  grid-template-columns: max-content minmax(320px, 520px);
  gap: 18px;
  align-items: start;
  border: 1px solid #263041;
  background: #080b10;
  padding: 14px;
  border-radius: 6px;
}}
pre.map {{
  margin: 0;
  line-height: 1.1;
  font-size: 18px;
  letter-spacing: 0;
}}
.panel {{
  background: #0d1117;
  border: 1px solid #263041;
  border-radius: 6px;
  padding: 12px;
  white-space: pre-wrap;
  font-size: 13px;
  line-height: 1.35;
}}
.wall {{ color: #a5aab5; }}
.floor {{ color: #52dc66; }}
.door {{ color: #e0a658; }}
.open {{ color: #add896; }}
.trap {{ color: #e75c5c; }}
.chest {{ color: #eec661; }}
.objective {{ color: #ffd770; font-weight: 700; }}
.exit {{ color: #6ac0ff; }}
.active-hero {{ color: #ffffff; font-weight: 700; }}
.hero-b {{ color: #ff7575; font-weight: 700; }}
.hero-w {{ color: #ac84ff; font-weight: 700; }}
.hero-e {{ color: #5ddc92; font-weight: 700; }}
.hero-d {{ color: #f4be64; font-weight: 700; }}
.monster {{ color: #ff7857; font-weight: 700; }}
.dim {{ color: #28303a; }}
@media (max-width: 900px) {{ .frame {{ grid-template-columns: 1fr; overflow-x: auto; }} }}
</style>
</head>
<body>
<header><h1>{escape(title)}</h1></header>
<main class="frames">
{frame_html}
</main>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")
    return path


def _font(ImageFont, size: int):
    for name in ("Menlo.ttc", "Menlo.ttf", "DejaVuSansMono.ttf", "Courier New.ttf"):
        try:
            return ImageFont.truetype(name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _grid_from_state(state: dict[str, Any]) -> list[list[tuple[str, str]]]:
    width = int(state.get("width", 0))
    height = int(state.get("height", 0))
    terrain = state.get("terrain")
    if isinstance(terrain, list) and terrain:
        chars = [[str(cell)[:1] if cell else " " for cell in row] for row in terrain]
    else:
        chars = [[" " for _ in range(width)] for _ in range(height)]
    if not chars and width and height:
        chars = [[" " for _ in range(width)] for _ in range(height)]
    chars = _nethack_wall_glyphs(chars)
    styles = [[_base_class_for_char(char) for char in row] for row in chars]
    known = _known_tiles(state)
    party_visible = state.get("visibility") not in {"omniscient", "private", "warden"}
    for y, row in enumerate(chars):
        for x, char in enumerate(row):
            if party_visible and known and (x, y) not in known:
                styles[y][x] = "dim"
            elif char == ".":
                row[x] = "."
                styles[y][x] = "floor"

    _place_static(chars, styles, state, known if party_visible else None)
    _place_entities(chars, styles, state, known if party_visible else None)
    return [[(char, styles[y][x]) for x, char in enumerate(row)] for y, row in enumerate(chars)]


def _known_tiles(state: dict[str, Any]) -> set[tuple[int, int]]:
    known_raw = state.get("known_tiles") or []
    known: set[tuple[int, int]] = set()
    for pos in known_raw:
        if isinstance(pos, (list, tuple)) and len(pos) == 2:
            known.add((int(pos[0]), int(pos[1])))
    return known


def _nethack_wall_glyphs(chars: list[list[str]]) -> list[list[str]]:
    result = [list(row) for row in chars]
    for y, row in enumerate(chars):
        for x, char in enumerate(row):
            if char != "#":
                continue
            left_open = _is_open_terrain(chars, x - 1, y)
            right_open = _is_open_terrain(chars, x + 1, y)
            up_open = _is_open_terrain(chars, x, y - 1)
            down_open = _is_open_terrain(chars, x, y + 1)
            if (left_open or right_open) and not (up_open or down_open):
                result[y][x] = "|"
            elif up_open or down_open:
                result[y][x] = "-"
            else:
                result[y][x] = "#"
    return result


def _is_open_terrain(chars: list[list[str]], x: int, y: int) -> bool:
    if y < 0 or y >= len(chars) or x < 0 or x >= len(chars[y]):
        return False
    return chars[y][x] in {
        ".",
        "/",
        "D",
        "C",
        "I",
        "E",
        "^",
        "T",
        "A",
        "a",
        "d",
        "v",
        "l",
        "s",
        "$",
        "f",
    }


def _place_static(
    grid: list[list[str]],
    styles: list[list[str]],
    state: dict[str, Any],
    known: set[tuple[int, int]] | None,
) -> None:
    _set_pos(grid, styles, state.get("entry"), "E", "exit", known)
    _set_pos(grid, styles, state.get("escape_tile"), "E", "exit", known)
    for door in (state.get("doors") or {}).values():
        if door.get("secret") and not door.get("discovered"):
            continue
        glyph = "/" if door.get("state") == "open" else "D"
        _set_pos(grid, styles, door.get("pos"), glyph, "open" if glyph == "/" else "door", known)
    for trap in (state.get("traps") or {}).values():
        if trap.get("revealed") and trap.get("armed", True):
            _set_pos(grid, styles, trap.get("pos"), "^", "trap", known)
    for chest in (state.get("chests") or {}).values():
        if not chest.get("opened"):
            _set_pos(grid, styles, chest.get("pos"), "C", "chest", known)
    furniture_glyphs = {
        "armory": "A",
        "altar": "a",
        "signal": "d",
        "hazard": "v",
        "lore": "l",
        "supply": "s",
        "treasure": "$",
    }
    for furniture in (state.get("furniture") or {}).values():
        if furniture.get("visible") and not furniture.get("destroyed"):
            glyph = furniture_glyphs.get(str(furniture.get("category")), "f")
            _set_pos(grid, styles, furniture.get("pos"), glyph, "furniture", known)
        elif furniture.get("destroyed"):
            _set_pos(grid, styles, furniture.get("pos"), "%", "dim", known)
    objective = state.get("objective") or {}
    if objective.get("pos") and not objective.get("carrier") and not objective.get("recovered"):
        _set_pos(grid, styles, objective.get("pos"), "I", "objective", known)


def _place_entities(
    grid: list[list[str]],
    styles: list[list[str]],
    state: dict[str, Any],
    known: set[tuple[int, int]] | None,
) -> None:
    role_glyphs = {
        "barbarian": ("B", "hero-b"),
        "wizard": ("W", "hero-w"),
        "elf": ("E", "hero-e"),
        "dwarf": ("D", "hero-d"),
    }
    monster_glyphs = {
        "skitterling": "g",
        "bone_guard": "b",
        "gloom_cultist": "k",
        "crypt_brute": "r",
        "lantern_wight": "w",
        "rat_pack": "p",
        "iron_sentinel": "n",
        "tusk_mauler": "m",
        "cinder_mage": "f",
        "mirror_adept": "y",
        "hollow_knight": "h",
    }
    active_agent = state.get("active_agent")
    for hero in (state.get("heroes") or {}).values():
        if hero.get("alive", True):
            if hero.get("id") == active_agent:
                glyph, css = "@", "active-hero"
            else:
                glyph, css = role_glyphs.get(hero.get("role"), ("@", "hero-b"))
            _set_pos(grid, styles, hero.get("pos"), glyph, css)
    for monster in (state.get("monsters") or {}).values():
        if monster.get("alive", True):
            _set_pos(
                grid,
                styles,
                monster.get("pos"),
                monster_glyphs.get(monster.get("role"), "m"),
                "monster",
                known,
            )


def _set_pos(
    grid: list[list[str]],
    styles: list[list[str]],
    pos: Any,
    glyph: str,
    css: str,
    known: set[tuple[int, int]] | None = None,
) -> None:
    if not isinstance(pos, (list, tuple)) or len(pos) != 2:
        return
    x, y = int(pos[0]), int(pos[1])
    if known is not None and (x, y) not in known:
        return
    if 0 <= y < len(grid) and 0 <= x < len(grid[y]):
        grid[y][x] = glyph
        styles[y][x] = css


def _base_class_for_char(char: str) -> str:
    return {
        "#": "wall",
        "-": "wall",
        "|": "wall",
        "+": "door",
        ".": "floor",
        " ": "dim",
        "D": "door",
        "/": "open",
        "^": "trap",
        "T": "trap",
        "C": "chest",
        "I": "objective",
        "E": "exit",
    }.get(
        char,
        "monster" if char in {"g", "b", "k", "r", "w", "p", "n", "m", "f", "y", "h"} else "dim",
    )


def _draw_grid(draw, grid, x0: int, y0: int, font) -> None:
    for y, row in enumerate(grid):
        for x, (char, css_class) in enumerate(row):
            color = _color_for(char, css_class)
            draw.text((x0 + x * CELL_W, y0 + y * CELL_H), char, fill=color, font=font)


def _draw_terminal(
    draw, grid, state: dict[str, Any], events: dict[str, Any], x0: int, y0: int, font
) -> None:
    lines = _terminal_lines(grid, state, events)
    styles = _terminal_styles(grid, lines)
    for y, line in enumerate(lines):
        for x, char in enumerate(line[:TERM_COLS]):
            if char == " ":
                continue
            css_class = styles.get((x, y), "status" if y >= TERM_ROWS - 2 else "dim")
            if css_class == "message":
                color = MESSAGE_FG
            elif css_class == "status":
                color = FG
            else:
                color = _color_for(char, css_class)
            draw.text((x0 + x * CELL_W, y0 + y * CELL_H), char, fill=color, font=font)


def _terminal_lines(
    grid: list[list[tuple[str, str]]], state: dict[str, Any], events: dict[str, Any]
) -> list[str]:
    rows = [" " * TERM_COLS for _ in range(TERM_ROWS)]
    message = _terminal_message(state, events)
    rows[0] = message[:TERM_COLS].ljust(TERM_COLS)

    map_rows = ["".join(char for char, _css in row) for row in grid]
    map_width = max((len(row) for row in map_rows), default=0)
    map_height = len(map_rows)
    map_x = _map_origin_x(map_width)
    map_y = 4
    for row_idx, row in enumerate(map_rows[: TERM_ROWS - 7]):
        y = map_y + row_idx
        if y >= TERM_ROWS - 4:
            break
        visible = row[: max(0, TERM_COLS - map_x)]
        rows[y] = _overlay(rows[y], map_x, visible)

    info_rows = _terminal_info_rows(state, events)
    start = max(map_y + map_height + 1, TERM_ROWS - 6)
    for index, line in enumerate(info_rows[:3]):
        y = min(start + index, TERM_ROWS - 3)
        rows[y] = line[:TERM_COLS].ljust(TERM_COLS)

    rows[-2] = _status_line_one(state)[:TERM_COLS].ljust(TERM_COLS)
    rows[-1] = _status_line_two(state, events)[:TERM_COLS].ljust(TERM_COLS)
    return rows


def _terminal_styles(
    grid: list[list[tuple[str, str]]], lines: list[str]
) -> dict[tuple[int, int], str]:
    styles: dict[tuple[int, int], str] = {}
    map_rows = ["".join(char for char, _css in row) for row in grid]
    map_width = max((len(row) for row in map_rows), default=0)
    map_x = _map_origin_x(map_width)
    map_y = 4
    for row_idx, row in enumerate(grid[: TERM_ROWS - 7]):
        y = map_y + row_idx
        if y >= TERM_ROWS - 4:
            break
        for x_idx, (_char, css) in enumerate(row[: max(0, TERM_COLS - map_x)]):
            styles[(map_x + x_idx, y)] = css
    for y, line in enumerate(lines):
        if y >= TERM_ROWS - 2:
            continue
        if y == 0:
            for x, char in enumerate(line):
                if char != " ":
                    styles[(x, y)] = "message"
        elif y < map_y or y >= TERM_ROWS - 6:
            for x, char in enumerate(line):
                if char != " ":
                    styles[(x, y)] = "status"
    return styles


def _map_origin_x(map_width: int) -> int:
    if map_width <= 0:
        return 2
    return min(max(8, (TERM_COLS - map_width) // 2), max(2, TERM_COLS - map_width - 2))


def _overlay(base: str, x: int, text: str) -> str:
    chars = list(base)
    for idx, char in enumerate(text):
        pos = x + idx
        if 0 <= pos < len(chars):
            chars[pos] = char
    return "".join(chars)


def _terminal_message(state: dict[str, Any], events: dict[str, Any]) -> str:
    skipped = events.get("skipped_actions") or events.get("skipped_illegal_actions") or []
    if skipped:
        reason = skipped[-1].get("reason") if isinstance(skipped[-1], dict) else None
        return f"Invalid action skipped: {reason or _compact(skipped[-1])}"
    event_log = state.get("event_log_tail") or []
    if event_log:
        return str(event_log[-1])
    title = str(state.get("title") or state.get("quest_id") or "DungeonGrid")
    active = _active_hero(state)
    if active:
        return f"{title}.  {active.get('role', 'hero').title()} enters the dark."
    return f"{title}."


def _terminal_info_rows(state: dict[str, Any], events: dict[str, Any]) -> list[str]:
    rows = []
    actions = events.get("executed_actions") or []
    if actions:
        rows.append("You do: " + "; ".join(_action_phrase(action) for action in actions[-3:]))
    achievements = events.get("new_achievements") or []
    if achievements:
        rows.append(
            "Achievement: "
            + ", ".join(
                str(item.get("id") or item.get("title") or item) for item in achievements[-2:]
            )
        )
    messages = state.get("party_messages_tail") or []
    if messages:
        message = messages[-1]
        text = message.get("text") or message.get("message") or message.get("payload") or ""
        rows.append(
            f"{message.get('from', '?')} whispers to {message.get('to', 'party')}: {text!s}"
        )
    if not rows:
        objective = state.get("objective") or {}
        rows.append(
            f"Objective: {objective.get('id', '-')} carrier={objective.get('carrier') or '-'} "
            f"recovered={objective.get('recovered')} dread={state.get('dread', '-')}"
        )
    return rows


def _status_line_one(state: dict[str, Any]) -> str:
    hero = _active_hero(state)
    if not hero:
        return "No active hero"
    role = str(hero.get("role") or "hero").title()
    attack = hero.get("attack", "-")
    guard = hero.get("guard", "-")
    speed = hero.get("speed", "-")
    focus = hero.get("focus", "-")
    hp = f"{hero.get('hp')}({hero.get('max_hp')})"
    ap = state.get("ap_remaining", {}).get(hero.get("id"), "-")
    weapon = (hero.get("equipment") or {}).get("weapon", "unarmed")
    return f"{role} the Adventurer       Wpn:{weapon} At:{attack} Gd:{guard} Sp:{speed} Fo:{focus} HP:{hp} AP:{ap}"


def _status_line_two(state: dict[str, Any], events: dict[str, Any]) -> str:
    party = " ".join(_party_hp_labels(state))
    objective = (state.get("objective") or {}).get("id") or "-"
    reward = events.get("reward", 0)
    return (
        f"Dlvl:{state.get('quest_id', '-')} $:{state.get('treasure_collected', 0)} "
        f"Torch:{state.get('torch')} Alert:{state.get('alert')} Dread:{state.get('dread', '-')} Obj:{objective} "
        f"R:{state.get('round')} +{reward} {party}"
    )


def _active_hero(state: dict[str, Any]) -> dict[str, Any] | None:
    active = state.get("active_agent")
    hero = (state.get("heroes") or {}).get(active)
    return hero if isinstance(hero, dict) else None


def _party_hp_labels(state: dict[str, Any]) -> list[str]:
    labels = []
    glyphs = {"barbarian": "B", "wizard": "W", "elf": "E", "dwarf": "D"}
    for hero in (state.get("heroes") or {}).values():
        glyph = glyphs.get(hero.get("role"), "?")
        labels.append(f"{glyph}:{hero.get('hp')}/{hero.get('max_hp')}")
    return labels


def _action_phrase(action: Any) -> str:
    if not isinstance(action, dict):
        return str(action)
    action_type = action.get("type", "?")
    if action_type == "move":
        return f"move {action.get('direction', '?')}"
    if action_type == "sneak":
        return f"sneak {action.get('direction', '?')}"
    if action_type == "open_door":
        return "open door"
    if action_type == "search":
        return f"search {action.get('target', '')}".strip()
    if action_type == "search_traps":
        return "search traps"
    if action_type == "search_secrets":
        return "search secrets"
    if action_type == "search_treasure":
        return f"search treasure {action.get('target', '')}".strip()
    if action_type == "search_furniture":
        return f"search furniture {action.get('target', '')}".strip()
    if action_type == "attack_object":
        return f"break {action.get('target', '')}".strip()
    if action_type == "distract":
        return f"distract {action.get('target', '')}".strip()
    if action_type == "sabotage":
        return f"sabotage {action.get('target', '')}".strip()
    if action_type == "rig_trap":
        return f"rig trap {action.get('target', '')}".strip()
    if action_type == "equip_item":
        return f"equip {action.get('target', '')}".strip()
    if action_type == "give_item":
        payload = action.get("payload") if isinstance(action.get("payload"), dict) else {}
        return f"give {payload.get('item', '?')} to {action.get('target', '?')}"[:40]
    if action_type == "message":
        text = (
            action.get("payload", {}).get("text") if isinstance(action.get("payload"), dict) else ""
        )
        return f"message: {text}"[:40]
    if action_type == "attack":
        return f"attack {action.get('target', '?')}"
    if action_type == "cast":
        payload = action.get("payload") if isinstance(action.get("payload"), dict) else {}
        return f"cast {payload.get('spell', '?')} -> {action.get('target', '?')}"[:40]
    if action_type == "cast_spell":
        return f"cast {action.get('spell', action.get('target', '?'))}"
    return action_type


def _color_for(char: str, css_class: str) -> tuple[int, int, int]:
    if css_class == "dim":
        return DIM
    if css_class == "active-hero":
        return COLORS["@"]
    if css_class == "hero-e":
        return COLORS["E_HERO"]
    if css_class == "hero-d":
        return COLORS["D_HERO"]
    return COLORS.get(char, FG)


def _draw_panel(
    draw, state: dict[str, Any], events: dict[str, Any], x: int, y: int, right: int, font, small
) -> None:
    lines = _panel_lines(state, events)
    yy = y
    for index, line in enumerate(lines):
        fill = (
            FG
            if index < 7 or line.startswith(("actions", "events", "achievements", "messages"))
            else DIM
        )
        draw.text((x, yy), line[:58], fill=fill, font=font if index == 0 else small)
        yy += 22 if index == 0 else 18
        if yy > 500:
            break


def _panel_lines(state: dict[str, Any], events: dict[str, Any]) -> list[str]:
    objective = state.get("objective") or {}
    active = state.get("active_agent")
    lines = [
        f"{state.get('title', state.get('quest_id', 'DungeonGrid'))}",
        f"round {state.get('round')}  phase {state.get('phase')}  active {state.get('active_agent')}",
        f"AP {state.get('ap_remaining', {}).get(state.get('active_agent'), '-')}"
        f"  move {(state.get('movement_remaining') or {}).get(active, '-')}"
        f"  alert {state.get('alert')}  dread {state.get('dread', '-')}"
        f"  torch {state.get('torch')}",
        f"objective {objective.get('id')} carrier={objective.get('carrier') or '-'} recovered={objective.get('recovered')}",
        f"extracted {len(state.get('extracted_heroes') or [])}  termination {state.get('termination_reason') or '-'}",
        f"reward {events.get('reward', 0)}  step {events.get('step_index', '-')}",
        "",
        "heroes:",
    ]
    for hero_id, hero in (state.get("heroes") or {}).items():
        hp = f"{hero.get('hp')}/{hero.get('max_hp')}"
        ap = state.get("ap_remaining", {}).get(hero_id, "-")
        status = "" if hero.get("alive", True) else " down"
        lines.append(f"  {hero_id} {hero.get('role')} hp {hp} ap {ap}{status}")
    lines.append("")
    lines.append("actions:")
    for action in (events.get("executed_actions") or [])[-4:]:
        lines.append(f"  {_compact(action)}")
    skipped = events.get("skipped_actions") or events.get("skipped_illegal_actions") or []
    if skipped:
        lines.append("invalid/skipped:")
        for action in skipped[-3:]:
            lines.append(f"  {_compact(action)}")
    achievements = events.get("new_achievements") or []
    if achievements:
        lines.append("achievements:")
        for achievement in achievements[-3:]:
            lines.append(f"  {achievement.get('title') or achievement.get('id')}")
    messages = state.get("party_messages_tail") or []
    if messages:
        lines.append("messages:")
        for message in messages[-3:]:
            text = message.get("text") or message.get("message") or message.get("payload") or ""
            lines.append(
                f"  {message.get('from', '?')}->{message.get('to', 'party')}: {str(text)[:42]}"
            )
    event_log = state.get("event_log_tail") or []
    if event_log:
        lines.append("events:")
        for event in event_log[-4:]:
            lines.append(f"  {str(event)[:54]}")
    return lines


def _compact(value: Any) -> str:
    text = json.dumps(value, sort_keys=True) if not isinstance(value, str) else value
    return text if len(text) <= 58 else text[:55] + "..."


def _frame_events(frame: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in frame.items() if key != "state"}


def _title_from_frames(frames: list[dict[str, Any]]) -> str:
    state = frames[0].get("state") if frames else {}
    if isinstance(state, dict):
        return f"DungeonGrid Replay: {state.get('title') or state.get('quest_id') or 'episode'}"
    return "DungeonGrid Replay"


def _html_frame(frame: dict[str, Any], index: int) -> str:
    state = frame.get("state") or {}
    grid = _grid_from_state(state) if isinstance(state, dict) else []
    map_html = "\n".join(
        "".join(f'<span class="{css}">{escape(char)}</span>' for char, css in row) for row in grid
    )
    panel = "\n".join(escape(line) for line in _panel_lines(state, _frame_events(frame)))
    return f"""<section class="frame" id="frame-{index}">
<pre class="map">{map_html}</pre>
<div class="panel">{panel}</div>
</section>"""
