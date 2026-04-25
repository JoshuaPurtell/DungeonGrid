"""Sprite-style DungeonGrid replay rendering.

The renderer uses procedural pixel-art-like shapes so DungeonGrid can ship a
good visual replay without carrying binary sprite assets.
"""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any


TILE = 34
PAD = 18
HUD_W = 300
MSG_H = 54
BG = (9, 10, 14)
PANEL = (20, 22, 29)
TEXT = (235, 230, 215)
MUTED = (148, 142, 132)
GOLD = (236, 190, 96)
RED = (220, 82, 76)
GREEN = (96, 204, 117)
BLUE = (92, 166, 222)


def render_sprite_frame(
    state_json: dict[str, Any],
    events: dict[str, Any] | None = None,
    tile_px: int = TILE,
):
    """Render a DungeonGrid state as a polished sprite-board PIL image."""

    try:
        from PIL import Image, ImageDraw, ImageFont
    except ImportError as exc:  # pragma: no cover - depends on optional extra
        raise ImportError("Install dungeongrid[render] to render sprite frames.") from exc

    events = events or {}
    tile = max(20, int(tile_px))
    width = int(state_json.get("width", 0))
    height = int(state_json.get("height", 0))
    board_w = width * tile
    board_h = height * tile
    canvas_w = PAD * 3 + board_w + HUD_W
    canvas_h = PAD * 3 + MSG_H + board_h

    image = Image.new("RGB", (canvas_w, canvas_h), BG)
    draw = ImageDraw.Draw(image)
    font = _font(ImageFont, 15)
    small = _font(ImageFont, 12)
    title_font = _font(ImageFont, 18)

    _draw_message_bar(draw, state_json, events, PAD, PAD, board_w + HUD_W + PAD, MSG_H, title_font, font)
    board_x = PAD
    board_y = PAD * 2 + MSG_H
    _draw_board_backdrop(draw, board_x, board_y, board_w, board_h)
    _draw_tiles(draw, state_json, board_x, board_y, tile)
    _draw_statics(draw, state_json, board_x, board_y, tile)
    _draw_action_trails(draw, state_json, events, board_x, board_y, tile)
    _draw_entities(draw, state_json, board_x, board_y, tile, font)
    _draw_hud(draw, state_json, events, board_x + board_w + PAD, board_y, HUD_W, board_h, title_font, font, small)
    return image


def render_sprite_gif(frames: list[dict[str, Any]], path: str | Path, fps: int = 2, tile_px: int = TILE) -> Path:
    """Render replay frames to an animated sprite GIF."""

    if not frames:
        raise ValueError("Cannot render an empty DungeonGrid replay.")
    try:
        import imageio.v2 as imageio
    except ImportError as exc:  # pragma: no cover - depends on optional extra
        raise ImportError("Install dungeongrid[render] to render sprite GIF replays.") from exc

    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    images = [
        render_sprite_frame(frame["state"], events=_frame_events(frame), tile_px=tile_px)
        for frame in frames
        if isinstance(frame.get("state"), dict)
    ]
    if not images:
        raise ValueError("DungeonGrid replay frames do not include state payloads.")
    imageio.mimsave(path, images, duration=1 / max(int(fps), 1))
    return path


def render_sprite_html(frames: list[dict[str, Any]], path: str | Path, title: str | None = None) -> Path:
    """Write a compact HTML index for sprite replay artifacts."""

    if not frames:
        raise ValueError("Cannot render an empty DungeonGrid replay.")
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    title = title or _title_from_frames(frames)
    rows = "\n".join(_html_frame(frame, index) for index, frame in enumerate(frames))
    gif_name = path.with_suffix(".gif").name
    html = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<style>
body {{
  margin: 0;
  background: #090a0e;
  color: #ebe6d7;
  font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}}
header {{ position: sticky; top: 0; background: #14161d; border-bottom: 1px solid #34313a; padding: 12px 18px; }}
h1 {{ font-size: 18px; margin: 0; }}
main {{ padding: 18px; display: grid; gap: 14px; }}
.hero {{ border: 1px solid #34313a; background: #101219; border-radius: 8px; padding: 12px; }}
.hero img {{ max-width: 100%; height: auto; image-rendering: pixelated; border-radius: 6px; }}
section {{ border: 1px solid #34313a; background: #101219; border-radius: 8px; padding: 12px; }}
.meta {{ color: #948e84; font-size: 13px; margin-bottom: 8px; }}
pre {{ white-space: pre-wrap; margin: 0; color: #ebe6d7; font-size: 12px; }}
</style>
</head>
<body>
<header><h1>{escape(title)}</h1></header>
<main>
<div class="hero"><img src="{escape(gif_name)}" alt="{escape(title)}"></div>
{rows}
</main>
</body>
</html>
"""
    path.write_text(html, encoding="utf-8")
    return path


def _font(ImageFont, size: int):
    for name in ("Avenir Next.ttc", "Menlo.ttc", "DejaVuSans.ttf", "Arial.ttf"):
        try:
            return ImageFont.truetype(name, size=size)
        except OSError:
            continue
    return ImageFont.load_default()


def _draw_message_bar(draw, state: dict[str, Any], events: dict[str, Any], x: int, y: int, w: int, h: int, title_font, font) -> None:
    draw.rounded_rectangle((x, y, x + w, y + h), radius=10, fill=(18, 20, 27), outline=(54, 49, 58))
    message = _message(state, events)
    draw.text((x + 14, y + 9), message[:96], fill=(244, 229, 182), font=title_font)
    subtitle = f"Round {state.get('round')}   Active {_active_role(state)}   Torch {state.get('torch')}   Alert {state.get('alert')}"
    draw.text((x + 14, y + 32), subtitle, fill=MUTED, font=font)


def _draw_board_backdrop(draw, x: int, y: int, w: int, h: int) -> None:
    draw.rounded_rectangle((x - 6, y - 6, x + w + 6, y + h + 6), radius=12, fill=(12, 12, 17), outline=(52, 49, 58))


def _draw_tiles(draw, state: dict[str, Any], x0: int, y0: int, tile: int) -> None:
    terrain = _terrain(state)
    known = _known_tiles(state)
    party_visible = state.get("visibility") not in {"omniscient", "private", "warden"}
    for y, row in enumerate(terrain):
        for x, char in enumerate(row):
            known_tile = not party_visible or not known or (x, y) in known
            box = _tile_box(x0, y0, x, y, tile)
            if char == "#":
                _draw_wall(draw, box, known_tile)
            elif char == " ":
                draw.rectangle(box, fill=(5, 6, 8))
            else:
                _draw_floor(draw, box, known_tile, (x + y) % 2 == 0)


def _draw_floor(draw, box: tuple[int, int, int, int], known: bool, alt: bool) -> None:
    color = (47, 42, 44) if alt else (42, 38, 42)
    if not known:
        color = (20, 22, 28)
    draw.rectangle(box, fill=color)
    x1, y1, x2, y2 = box
    line = (60, 54, 56) if known else (30, 33, 40)
    draw.line((x1, y2 - 1, x2, y2 - 1), fill=line)
    draw.line((x2 - 1, y1, x2 - 1, y2), fill=line)
    if known:
        draw.point((x1 + 8, y1 + 9), fill=(73, 65, 62))
        draw.point((x1 + 22, y1 + 23), fill=(31, 29, 32))


def _draw_wall(draw, box: tuple[int, int, int, int], known: bool) -> None:
    base = (84, 81, 88) if known else (29, 32, 39)
    hi = (118, 112, 120) if known else (43, 47, 56)
    lo = (45, 43, 50) if known else (18, 20, 25)
    x1, y1, x2, y2 = box
    draw.rectangle(box, fill=base)
    draw.rectangle((x1 + 2, y1 + 2, x2 - 3, y1 + 10), fill=hi)
    draw.rectangle((x1 + 2, y1 + 21, x2 - 3, y2 - 3), fill=lo)
    draw.line((x1, y1, x2, y1), fill=(150, 140, 132) if known else hi)
    draw.line((x1, y2 - 1, x2, y2 - 1), fill=lo)


def _draw_statics(draw, state: dict[str, Any], x0: int, y0: int, tile: int) -> None:
    known = _known_tiles(state)
    party_visible = state.get("visibility") not in {"omniscient", "private", "warden"}
    visible = None if not party_visible else known
    _draw_marker(draw, state.get("entry"), x0, y0, tile, "stairs", visible)
    _draw_marker(draw, state.get("escape_tile"), x0, y0, tile, "exit", visible)
    for door in (state.get("doors") or {}).values():
        if door.get("secret") and not door.get("discovered"):
            continue
        _draw_marker(draw, door.get("pos"), x0, y0, tile, "open_door" if door.get("state") == "open" else "door", visible)
    for trap in (state.get("traps") or {}).values():
        if trap.get("revealed") and trap.get("armed", True):
            _draw_marker(draw, trap.get("pos"), x0, y0, tile, "trap", visible)
    for chest in (state.get("chests") or {}).values():
        if not chest.get("opened"):
            _draw_marker(draw, chest.get("pos"), x0, y0, tile, "chest", visible)
    for furniture in (state.get("furniture") or {}).values():
        if furniture.get("visible"):
            _draw_furniture(draw, furniture, x0, y0, tile, visible)
    objective = state.get("objective") or {}
    if objective.get("pos") and not objective.get("carrier") and not objective.get("recovered"):
        _draw_marker(draw, objective.get("pos"), x0, y0, tile, "objective", visible)


def _draw_marker(draw, pos: Any, x0: int, y0: int, tile: int, kind: str, visible: set[tuple[int, int]] | None) -> None:
    parsed = _pos(pos)
    if parsed is None:
        return
    x, y = parsed
    if visible is not None and (x, y) not in visible:
        return
    x1, y1, x2, y2 = _tile_box(x0, y0, x, y, tile)
    cx, cy = x1 + tile // 2, y1 + tile // 2
    if kind == "door":
        draw.rounded_rectangle((x1 + 9, y1 + 4, x2 - 9, y2 - 3), radius=3, fill=(130, 83, 46), outline=(225, 159, 78))
        draw.ellipse((cx + 4, cy, cx + 7, cy + 3), fill=GOLD)
    elif kind == "open_door":
        draw.polygon([(x1 + 10, y1 + 5), (x1 + 20, y1 + 2), (x1 + 20, y2 - 4), (x1 + 10, y2 - 2)], fill=(106, 70, 42), outline=(180, 129, 73))
    elif kind == "chest":
        draw.rounded_rectangle((x1 + 6, y1 + 13, x2 - 6, y2 - 5), radius=4, fill=(142, 89, 44), outline=(232, 177, 82))
        draw.rectangle((x1 + 8, y1 + 10, x2 - 8, y1 + 18), fill=(179, 111, 48))
        draw.rectangle((cx - 2, cy + 1, cx + 3, cy + 6), fill=GOLD)
    elif kind == "trap":
        draw.polygon([(cx, y1 + 6), (x2 - 7, y2 - 7), (x1 + 7, y2 - 7)], outline=RED, fill=(80, 28, 31))
        draw.text((cx - 4, y1 + 10), "!", fill=(255, 188, 120))
    elif kind == "objective":
        draw.ellipse((cx - 9, cy - 10, cx + 9, cy + 10), fill=(235, 179, 65), outline=(255, 238, 156), width=2)
        draw.ellipse((cx - 3, cy - 4, cx + 3, cy + 4), fill=(118, 35, 42))
    elif kind in {"stairs", "exit"}:
        color = BLUE if kind == "exit" else (117, 201, 142)
        draw.polygon([(cx, y1 + 7), (x2 - 8, cy), (cx, y2 - 7), (x1 + 8, cy)], fill=(24, 42, 55), outline=color)


def _draw_furniture(draw, furniture: dict[str, Any], x0: int, y0: int, tile: int, visible: set[tuple[int, int]] | None) -> None:
    pos = _pos(furniture.get("pos"))
    if pos is None:
        return
    if visible is not None and pos not in visible:
        return
    x1, y1, x2, y2 = _tile_box(x0, y0, pos[0], pos[1], tile)
    cx, cy = x1 + tile // 2, y1 + tile // 2
    if furniture.get("destroyed"):
        draw.line((x1 + 9, y1 + 23, x2 - 8, y1 + 11), fill=(116, 92, 72), width=3)
        draw.line((x1 + 10, y1 + 11, x2 - 9, y1 + 24), fill=(88, 68, 56), width=3)
        return
    category = str(furniture.get("category") or "furniture")
    colors = {
        "armory": ((118, 88, 56), (205, 211, 215)),
        "altar": ((92, 76, 104), (232, 166, 74)),
        "signal": ((128, 76, 44), (223, 164, 86)),
        "hazard": ((92, 62, 48), (238, 97, 65)),
        "lore": ((88, 62, 45), (213, 190, 130)),
        "supply": ((94, 76, 45), (117, 201, 142)),
        "treasure": ((120, 76, 39), GOLD),
    }
    base, accent = colors.get(category, ((92, 72, 55), (180, 155, 111)))
    draw.rounded_rectangle((x1 + 6, y1 + 11, x2 - 6, y2 - 5), radius=4, fill=base, outline=accent)
    if category == "armory":
        draw.line((cx - 8, y1 + 7, cx + 7, y2 - 6), fill=accent, width=2)
        draw.polygon([(cx + 6, y1 + 6), (cx + 12, y1 + 9), (cx + 8, y1 + 12)], fill=accent)
    elif category == "altar":
        draw.ellipse((cx - 5, y1 + 8, cx + 5, y1 + 18), fill=accent)
    elif category == "signal":
        draw.ellipse((cx - 11, y1 + 9, cx + 11, y1 + 24), fill=(84, 44, 31), outline=accent, width=2)
    elif category == "hazard":
        draw.arc((cx - 10, y1 + 6, cx + 10, y1 + 25), 200, 340, fill=accent, width=3)
    elif category == "lore":
        draw.rectangle((cx - 9, y1 + 8, cx + 9, y1 + 23), fill=(72, 43, 31), outline=accent)
        draw.line((cx, y1 + 9, cx, y1 + 22), fill=accent)
    elif category == "supply":
        draw.rectangle((cx - 10, y1 + 9, cx + 10, y1 + 24), fill=base, outline=accent)
        draw.line((cx - 7, y1 + 14, cx + 7, y1 + 14), fill=accent)
    elif category == "treasure":
        draw.rectangle((cx - 9, y1 + 13, cx + 9, y1 + 24), fill=base, outline=accent)
        draw.rectangle((cx - 2, y1 + 16, cx + 3, y1 + 21), fill=accent)
    if furniture.get("destructible"):
        hp = max(0, int(furniture.get("hp", 1)))
        max_hp = max(1, int(furniture.get("max_hp", hp or 1)))
        if hp < max_hp:
            draw.line((x1 + 7, y1 + 6, x2 - 7, y2 - 6), fill=RED, width=2)


def _draw_entities(draw, state: dict[str, Any], x0: int, y0: int, tile: int, font) -> None:
    known = _known_tiles(state)
    party_visible = state.get("visibility") not in {"omniscient", "private", "warden"}
    visible = None if not party_visible else known
    active = state.get("active_agent")
    for monster in (state.get("monsters") or {}).values():
        if monster.get("alive", True):
            pos = _pos(monster.get("pos"))
            if pos is not None and (visible is None or pos in visible):
                _draw_monster(draw, monster, pos, x0, y0, tile)
    for hero in (state.get("heroes") or {}).values():
        if hero.get("alive", True):
            pos = _pos(hero.get("pos"))
            if pos is not None:
                _draw_hero(draw, hero, pos, x0, y0, tile, font, active=hero.get("id") == active)


def _draw_action_trails(draw, state: dict[str, Any], events: dict[str, Any], x0: int, y0: int, tile: int) -> None:
    actions = events.get("executed_actions") or []
    if not actions:
        return
    heroes = state.get("heroes") or {}
    for action in actions[-3:]:
        if not isinstance(action, dict) or action.get("type") != "move":
            continue
        agent_id = action.get("agent_id") or events.get("agent_id")
        hero = heroes.get(agent_id)
        if not isinstance(hero, dict):
            continue
        pos = _pos(hero.get("pos"))
        if pos is None:
            continue
        direction = str(action.get("direction") or "")
        dx, dy = {
            "east": (-1, 0),
            "west": (1, 0),
            "south": (0, -1),
            "north": (0, 1),
        }.get(direction, (0, 0))
        if dx == 0 and dy == 0:
            continue
        trail = (pos[0] + dx, pos[1] + dy)
        _draw_footprints(draw, hero, trail, x0, y0, tile, direction)


def _draw_footprints(draw, hero: dict[str, Any], pos: tuple[int, int], x0: int, y0: int, tile: int, direction: str) -> None:
    role = str(hero.get("role") or "")
    color = {
        "barbarian": (198, 82, 72),
        "wizard": (130, 102, 222),
        "elf": (80, 172, 104),
        "dwarf": (210, 143, 64),
    }.get(role, (150, 160, 180))
    x, y = pos
    x1, y1, x2, y2 = _tile_box(x0, y0, x, y, tile)
    if x2 < x0 or y2 < y0:
        return
    cx, cy = x1 + tile // 2, y1 + tile // 2
    draw.ellipse((cx - 5, cy - 2, cx - 1, cy + 3), fill=color)
    draw.ellipse((cx + 2, cy + 2, cx + 6, cy + 7), fill=color)
    arrow = {
        "east": [(cx + 9, cy + 2), (cx + 14, cy), (cx + 9, cy - 2)],
        "west": [(cx - 9, cy + 2), (cx - 14, cy), (cx - 9, cy - 2)],
        "south": [(cx - 2, cy + 9), (cx, cy + 14), (cx + 2, cy + 9)],
        "north": [(cx - 2, cy - 9), (cx, cy - 14), (cx + 2, cy - 9)],
    }.get(direction)
    if arrow:
        draw.line(arrow, fill=color, width=2)


def _draw_hero(draw, hero: dict[str, Any], pos: tuple[int, int], x0: int, y0: int, tile: int, font, active: bool) -> None:
    role = str(hero.get("role") or "hero")
    x, y = pos
    x1, y1, _x2, _y2 = _tile_box(x0, y0, x, y, tile)
    cx, cy = x1 + tile // 2, y1 + tile // 2
    draw.ellipse((cx - 12, cy + 10, cx + 12, cy + 15), fill=(0, 0, 0))
    if active:
        draw.ellipse((cx - 16, cy - 16, cx + 16, cy + 16), outline=(255, 241, 159), width=3)
        draw.ellipse((cx - 14, cy - 14, cx + 14, cy + 14), outline=(119, 86, 36), width=1)
    if role == "barbarian":
        _draw_barbarian(draw, cx, cy)
    elif role == "wizard":
        _draw_wizard(draw, cx, cy)
    elif role == "elf":
        _draw_elf(draw, cx, cy)
    elif role == "dwarf":
        _draw_dwarf(draw, cx, cy)
    else:
        _draw_adventurer(draw, cx, cy)
    _draw_equipment_marks(draw, hero, cx, cy)
    _draw_hp_bar(draw, x1 + 4, y1 + 2, tile - 8, 4, hero.get("hp", 0), hero.get("max_hp", 1))


def _draw_equipment_marks(draw, hero: dict[str, Any], cx: int, cy: int) -> None:
    equipment = hero.get("equipment") or {}
    if equipment.get("offhand") == "shield":
        draw.ellipse((cx - 19, cy - 1, cx - 10, cy + 10), fill=(96, 118, 150), outline=(230, 218, 185))
    if equipment.get("cloak") == "warding_cloak":
        draw.arc((cx - 13, cy - 12, cx + 13, cy + 16), 35, 145, fill=(124, 190, 220), width=3)
    if equipment.get("helm") == "iron_helm":
        draw.arc((cx - 10, cy - 17, cx + 10, cy - 2), 180, 360, fill=(210, 211, 202), width=3)
    if equipment.get("charm") == "holy_charm":
        draw.ellipse((cx + 10, cy - 12, cx + 16, cy - 6), fill=GOLD, outline=(255, 246, 178))


def _draw_barbarian(draw, cx: int, cy: int) -> None:
    skin = (232, 164, 108)
    leather = (116, 68, 43)
    red = (202, 56, 50)
    steel = (205, 211, 215)
    draw.line((cx + 9, cy - 14, cx + 15, cy + 5), fill=(76, 52, 42), width=2)
    draw.polygon([(cx + 11, cy - 15), (cx + 18, cy - 11), (cx + 13, cy - 8)], fill=steel, outline=(80, 82, 88))
    draw.rectangle((cx - 8, cy - 2, cx + 8, cy + 12), fill=leather)
    draw.polygon([(cx - 9, cy - 2), (cx, cy + 8), (cx + 9, cy - 2)], fill=red)
    draw.ellipse((cx - 8, cy - 13, cx + 8, cy + 2), fill=skin, outline=(74, 42, 33))
    draw.rectangle((cx - 8, cy - 15, cx + 8, cy - 10), fill=(89, 48, 33))
    draw.line((cx - 12, cy + 1, cx - 5, cy + 7), fill=skin, width=3)
    draw.line((cx + 7, cy + 1, cx + 13, cy + 8), fill=skin, width=3)
    _draw_face(draw, cx, cy - 6)


def _draw_wizard(draw, cx: int, cy: int) -> None:
    robe = (98, 72, 184)
    trim = (222, 199, 92)
    skin = (222, 188, 151)
    draw.line((cx + 12, cy - 12, cx + 15, cy + 13), fill=(116, 74, 41), width=2)
    draw.ellipse((cx + 12, cy - 15, cx + 17, cy - 10), fill=(126, 216, 255))
    draw.polygon([(cx, cy - 20), (cx - 11, cy - 4), (cx + 11, cy - 4)], fill=robe, outline=(43, 38, 83))
    draw.arc((cx - 10, cy - 9, cx + 10, cy + 7), 185, 355, fill=trim, width=2)
    draw.polygon([(cx, cy - 1), (cx - 12, cy + 14), (cx + 12, cy + 14)], fill=robe, outline=(43, 38, 83))
    draw.ellipse((cx - 7, cy - 10, cx + 7, cy + 4), fill=skin, outline=(69, 46, 55))
    draw.rectangle((cx - 5, cy + 4, cx + 5, cy + 13), fill=(132, 99, 218))
    _draw_face(draw, cx, cy - 4)


def _draw_elf(draw, cx: int, cy: int) -> None:
    green = (54, 143, 86)
    light = (154, 219, 132)
    skin = (226, 181, 134)
    bow = (139, 85, 43)
    draw.arc((cx + 6, cy - 12, cx + 22, cy + 14), 90, 270, fill=bow, width=2)
    draw.line((cx + 14, cy - 9, cx + 14, cy + 10), fill=(230, 216, 158), width=1)
    draw.polygon([(cx, cy - 17), (cx - 12, cy - 4), (cx + 12, cy - 4)], fill=green, outline=(26, 78, 48))
    draw.ellipse((cx - 8, cy - 11, cx + 8, cy + 4), fill=skin, outline=(70, 48, 35))
    draw.polygon([(cx - 10, cy - 8), (cx - 16, cy - 5), (cx - 9, cy - 3)], fill=skin, outline=(70, 48, 35))
    draw.polygon([(cx + 10, cy - 8), (cx + 16, cy - 5), (cx + 9, cy - 3)], fill=skin, outline=(70, 48, 35))
    draw.polygon([(cx, cy + 1), (cx - 11, cy + 14), (cx + 11, cy + 14)], fill=green)
    draw.line((cx - 8, cy + 6, cx + 8, cy + 6), fill=light, width=2)
    _draw_face(draw, cx, cy - 5)


def _draw_dwarf(draw, cx: int, cy: int) -> None:
    armor = (114, 119, 124)
    beard = (207, 126, 54)
    helm = (183, 184, 174)
    skin = (222, 160, 111)
    hammer = (172, 172, 164)
    draw.line((cx + 11, cy - 10, cx + 16, cy + 9), fill=(91, 58, 35), width=3)
    draw.rectangle((cx + 10, cy - 13, cx + 20, cy - 7), fill=hammer, outline=(70, 70, 72))
    draw.rectangle((cx - 10, cy, cx + 10, cy + 13), fill=armor, outline=(48, 50, 54))
    draw.ellipse((cx - 9, cy - 12, cx + 9, cy + 4), fill=skin, outline=(77, 45, 34))
    draw.pieslice((cx - 10, cy - 15, cx + 10, cy - 2), 180, 360, fill=helm, outline=(74, 75, 78))
    draw.polygon([(cx - 8, cy - 1), (cx, cy + 13), (cx + 8, cy - 1)], fill=beard)
    draw.line((cx - 10, cy + 6, cx - 15, cy + 11), fill=armor, width=4)
    _draw_face(draw, cx, cy - 5)


def _draw_adventurer(draw, cx: int, cy: int) -> None:
    draw.rectangle((cx - 8, cy - 2, cx + 8, cy + 12), fill=(105, 122, 148))
    draw.ellipse((cx - 8, cy - 12, cx + 8, cy + 4), fill=(224, 182, 142), outline=(68, 42, 35))
    _draw_face(draw, cx, cy - 5)


def _draw_face(draw, cx: int, cy: int) -> None:
    eye = (24, 22, 24)
    draw.rectangle((cx - 4, cy - 1, cx - 2, cy + 1), fill=eye)
    draw.rectangle((cx + 3, cy - 1, cx + 5, cy + 1), fill=eye)
    draw.point((cx, cy + 3), fill=(86, 48, 40))


def _draw_monster(draw, monster: dict[str, Any], pos: tuple[int, int], x0: int, y0: int, tile: int) -> None:
    role = str(monster.get("role") or "monster")
    colors = {
        "skitterling": (105, 178, 83),
        "bone_guard": (202, 202, 190),
        "gloom_cultist": (167, 80, 183),
        "crypt_brute": (192, 76, 58),
        "lantern_wight": (101, 190, 220),
        "rat_pack": (126, 156, 98),
        "iron_sentinel": (158, 169, 176),
        "tusk_mauler": (190, 96, 62),
        "cinder_mage": (226, 93, 54),
        "mirror_adept": (166, 218, 230),
        "hollow_knight": (188, 184, 169),
    }
    color = colors.get(role, (188, 85, 78))
    x, y = pos
    x1, y1, _x2, _y2 = _tile_box(x0, y0, x, y, tile)
    cx, cy = x1 + tile // 2, y1 + tile // 2
    draw.ellipse((cx - 10, cy + 8, cx + 10, cy + 13), fill=(0, 0, 0))
    if role == "rat_pack":
        for ox, oy in [(-8, -2), (0, -7), (7, 0)]:
            draw.ellipse((cx + ox - 5, cy + oy - 4, cx + ox + 5, cy + oy + 5), fill=color, outline=(38, 28, 31))
            draw.ellipse((cx + ox + 1, cy + oy - 1, cx + ox + 3, cy + oy + 1), fill=(12, 10, 12))
    elif role == "iron_sentinel":
        draw.rectangle((cx - 12, cy - 12, cx + 12, cy + 11), fill=color, outline=(38, 28, 31))
        draw.rectangle((cx - 7, cy - 6, cx + 7, cy - 2), fill=(54, 62, 70))
        draw.line((cx - 13, cy + 1, cx + 13, cy + 1), fill=(90, 98, 106), width=2)
    elif role == "tusk_mauler":
        draw.rounded_rectangle((cx - 13, cy - 11, cx + 13, cy + 12), radius=7, fill=color, outline=(38, 28, 31))
        draw.polygon([(cx - 13, cy - 2), (cx - 22, cy + 2), (cx - 13, cy + 4)], fill=(230, 218, 185))
        draw.polygon([(cx + 13, cy - 2), (cx + 22, cy + 2), (cx + 13, cy + 4)], fill=(230, 218, 185))
        draw.ellipse((cx - 5, cy - 4, cx - 2, cy - 1), fill=(12, 10, 12))
        draw.ellipse((cx + 2, cy - 4, cx + 5, cy - 1), fill=(12, 10, 12))
    elif role == "cinder_mage":
        draw.polygon([(cx, cy - 14), (cx - 13, cy + 12), (cx + 13, cy + 12)], fill=color, outline=(38, 28, 31))
        draw.ellipse((cx - 7, cy - 11, cx + 7, cy + 3), fill=(70, 33, 40))
        draw.polygon([(cx + 8, cy - 12), (cx + 15, cy - 22), (cx + 13, cy - 8)], fill=GOLD)
    elif role == "mirror_adept":
        draw.polygon([(cx, cy - 14), (cx - 12, cy), (cx, cy + 14), (cx + 12, cy)], fill=color, outline=(38, 80, 90))
        draw.line((cx - 6, cy - 5, cx + 6, cy + 6), fill=(237, 250, 255), width=2)
    elif role == "hollow_knight":
        draw.rounded_rectangle((cx - 10, cy - 10, cx + 10, cy + 12), radius=5, fill=color, outline=(38, 28, 31))
        draw.rectangle((cx - 8, cy - 3, cx + 8, cy + 9), fill=(102, 104, 102), outline=(38, 28, 31))
        draw.ellipse((cx - 5, cy - 7, cx - 2, cy - 4), fill=(20, 18, 18))
        draw.ellipse((cx + 2, cy - 7, cx + 5, cy - 4), fill=(20, 18, 18))
    else:
        draw.rounded_rectangle((cx - 11, cy - 10, cx + 11, cy + 11), radius=8, fill=color, outline=(38, 28, 31))
        draw.ellipse((cx - 6, cy - 4, cx - 3, cy - 1), fill=(12, 10, 12))
        draw.ellipse((cx + 3, cy - 4, cx + 6, cy - 1), fill=(12, 10, 12))
        draw.line((cx - 5, cy + 5, cx + 5, cy + 5), fill=(36, 20, 22), width=2)
    _draw_hp_bar(draw, x1 + 5, y1 + 2, tile - 10, 3, monster.get("hp", 1), monster.get("max_hp", monster.get("hp", 1)))


def _draw_hp_bar(draw, x: int, y: int, w: int, h: int, hp: Any, max_hp: Any) -> None:
    try:
        hp_f = max(0.0, float(hp))
        max_f = max(1.0, float(max_hp))
    except (TypeError, ValueError):
        hp_f, max_f = 1.0, 1.0
    draw.rectangle((x, y, x + w, y + h), fill=(34, 20, 24))
    draw.rectangle((x, y, x + int(w * min(1.0, hp_f / max_f)), y + h), fill=RED if hp_f / max_f < 0.4 else GREEN)


def _draw_hud(draw, state: dict[str, Any], events: dict[str, Any], x: int, y: int, w: int, h: int, title_font, font, small) -> None:
    draw.rounded_rectangle((x, y, x + w, y + h), radius=12, fill=PANEL, outline=(54, 49, 58))
    yy = y + 14
    draw.text((x + 14, yy), str(state.get("title") or state.get("quest_id") or "DungeonGrid")[:26], fill=TEXT, font=title_font)
    yy += 32
    objective = state.get("objective") or {}
    lines = [
        f"Objective: {objective.get('id', '-')}",
        f"Carrier: {objective.get('carrier') or '-'}",
        f"Reward this turn: {events.get('reward', 0)}",
        "",
        "Party",
    ]
    for line in lines:
        draw.text((x + 14, yy), line, fill=GOLD if line == "Party" else MUTED, font=font)
        yy += 20
    for hero in (state.get("heroes") or {}).values():
        role = str(hero.get("role") or hero.get("id"))
        weapon = (hero.get("equipment") or {}).get("weapon", "-")
        draw.text((x + 22, yy), f"{role:<9} HP {hero.get('hp')}/{hero.get('max_hp')}", fill=TEXT, font=font)
        yy += 19
        draw.text((x + 32, yy), f"weapon: {weapon}", fill=MUTED, font=small)
        yy += 16
    yy += 8
    actions = events.get("executed_actions") or []
    if actions:
        draw.text((x + 14, yy), "Actions", fill=GOLD, font=font)
        yy += 20
        for action in actions[-4:]:
            draw.text((x + 22, yy), _action_phrase(action)[:32], fill=TEXT, font=small)
            yy += 17
    skipped = events.get("skipped_actions") or events.get("skipped_illegal_actions") or []
    if skipped:
        yy += 6
        draw.text((x + 14, yy), "Invalid", fill=(255, 142, 128), font=font)
        yy += 20
        for item in skipped[-3:]:
            draw.text((x + 22, yy), str(item)[:34], fill=(255, 190, 176), font=small)
            yy += 17
    achievements = events.get("new_achievements") or []
    if achievements:
        yy += 6
        draw.text((x + 14, yy), "Achievements", fill=GOLD, font=font)
        yy += 20
        for item in achievements[-3:]:
            draw.text((x + 22, yy), str(item.get("title") or item.get("id") or item)[:34], fill=TEXT, font=small)
            yy += 17


def _terrain(state: dict[str, Any]) -> list[list[str]]:
    width = int(state.get("width", 0))
    height = int(state.get("height", 0))
    terrain = state.get("terrain")
    if isinstance(terrain, list) and terrain:
        return [[str(cell)[:1] if cell else " " for cell in row] for row in terrain]
    return [[" " for _ in range(width)] for _ in range(height)]


def _known_tiles(state: dict[str, Any]) -> set[tuple[int, int]]:
    known_raw = state.get("known_tiles") or []
    known: set[tuple[int, int]] = set()
    for pos in known_raw:
        parsed = _pos(pos)
        if parsed is not None:
            known.add(parsed)
    return known


def _tile_box(x0: int, y0: int, x: int, y: int, tile: int) -> tuple[int, int, int, int]:
    return (x0 + x * tile, y0 + y * tile, x0 + (x + 1) * tile - 1, y0 + (y + 1) * tile - 1)


def _pos(pos: Any) -> tuple[int, int] | None:
    if not isinstance(pos, (list, tuple)) or len(pos) != 2:
        return None
    return int(pos[0]), int(pos[1])


def _active_role(state: dict[str, Any]) -> str:
    active = state.get("active_agent")
    hero = (state.get("heroes") or {}).get(active)
    if isinstance(hero, dict):
        return str(hero.get("role") or active)
    return str(active or "-")


def _message(state: dict[str, Any], events: dict[str, Any]) -> str:
    skipped = events.get("skipped_actions") or events.get("skipped_illegal_actions") or []
    if skipped:
        return "Invalid action skipped."
    event_log = state.get("event_log_tail") or []
    if event_log:
        return str(event_log[-1])
    return str(state.get("title") or state.get("quest_id") or "DungeonGrid")


def _action_phrase(action: Any) -> str:
    if not isinstance(action, dict):
        return str(action)
    action_type = action.get("type", "?")
    if action_type == "move":
        return f"move {action.get('direction', '?')}"
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
    if action_type == "equip_item":
        return f"equip {action.get('target', '')}".strip()
    if action_type == "give_item":
        payload = action.get("payload") if isinstance(action.get("payload"), dict) else {}
        return f"give {payload.get('item', '?')} to {action.get('target', '?')}"[:38]
    if action_type == "message":
        payload = action.get("payload") if isinstance(action.get("payload"), dict) else {}
        return f"message: {payload.get('text', '')}"[:38]
    if action_type == "attack":
        return f"attack {action.get('target', '?')}"
    if action_type == "cast":
        payload = action.get("payload") if isinstance(action.get("payload"), dict) else {}
        return f"cast {payload.get('spell', '?')} -> {action.get('target', '?')}"[:38]
    return str(action_type)


def _frame_events(frame: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in frame.items() if key != "state"}


def _title_from_frames(frames: list[dict[str, Any]]) -> str:
    state = frames[0].get("state") if frames else {}
    if isinstance(state, dict):
        return f"DungeonGrid Sprite Replay: {state.get('title') or state.get('quest_id') or 'episode'}"
    return "DungeonGrid Sprite Replay"


def _html_frame(frame: dict[str, Any], index: int) -> str:
    state = frame.get("state") or {}
    events = _frame_events(frame)
    lines = [
        f"step={events.get('step_index', index)} agent={events.get('agent_id', '-')}",
        f"actions={events.get('executed_actions', [])}",
        f"skipped={events.get('skipped_actions', [])}",
        f"events={events.get('events', [])}",
    ]
    return f"""<section>
<div class="meta">Frame {index}</div>
<pre>{escape(chr(10).join(lines))}</pre>
</section>"""
