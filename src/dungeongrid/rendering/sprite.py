"""Sprite-style DungeonGrid replay rendering.

The renderer uses a tiny 16x16 native sprite vocabulary and nearest-neighbor
scaling. The goal is benchmark-readable pixel art: Craftax-like granularity
with a warm old-school dungeon-board palette, without shipping binary sprite
assets or copying any protected board-game artwork.
"""

from __future__ import annotations

from html import escape
from pathlib import Path
from typing import Any

NATIVE_TILE = 16
TILE = 32
PAD = 18
HUD_W = 300
MSG_H = 54

# Warm, compact dungeon-board palette. Keep the renderer deliberately low-noise
# so replays remain legible as benchmark observations.
BG = (15, 12, 10)
PANEL = (32, 26, 23)
TEXT = (239, 226, 199)
MUTED = (157, 138, 112)
OUTLINE = (20, 17, 15)
VOID = (7, 7, 8)
STONE = (82, 82, 76)
STONE_LIGHT = (124, 120, 108)
WOOD_DARK = (72, 43, 24)
WOOD = (128, 76, 35)
WOOD_LIGHT = (178, 112, 48)
BONE = (218, 210, 184)
GOLD = (226, 174, 62)
RED = (177, 54, 49)
GREEN = (84, 145, 64)
BLUE = (57, 93, 154)
TORCH = (239, 119, 36)
BURGUNDY = (101, 40, 48)


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
    tile = max(NATIVE_TILE, int(tile_px))
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

    _draw_message_bar(
        draw, state_json, events, PAD, PAD, board_w + HUD_W + PAD, MSG_H, title_font, font
    )
    board_x = PAD
    board_y = PAD * 2 + MSG_H
    _draw_board_backdrop(draw, board_x, board_y, board_w, board_h)
    _draw_tiles(draw, state_json, board_x, board_y, tile)
    _draw_statics(draw, state_json, board_x, board_y, tile)
    _draw_action_trails(draw, state_json, events, board_x, board_y, tile)
    _draw_entities(draw, state_json, board_x, board_y, tile, font)
    _draw_hud(
        draw,
        state_json,
        events,
        board_x + board_w + PAD,
        board_y,
        HUD_W,
        board_h,
        title_font,
        font,
        small,
    )
    return image


def render_sprite_gif(
    frames: list[dict[str, Any]], path: str | Path, fps: int = 2, tile_px: int = TILE
) -> Path:
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


def render_sprite_html(
    frames: list[dict[str, Any]], path: str | Path, title: str | None = None
) -> Path:
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
  background: #0f0c0a;
  color: #efe2c7;
  font-family: ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
}}
header {{ position: sticky; top: 0; background: #201a17; border-bottom: 1px solid #4a3c2e; padding: 12px 18px; }}
h1 {{ font-size: 18px; margin: 0; }}
main {{ padding: 18px; display: grid; gap: 14px; }}
.hero {{ border: 1px solid #4a3c2e; background: #17120f; border-radius: 8px; padding: 12px; }}
.hero img {{ max-width: 100%; height: auto; image-rendering: pixelated; border-radius: 6px; }}
section {{ border: 1px solid #4a3c2e; background: #17120f; border-radius: 8px; padding: 12px; }}
.meta {{ color: #9d8a70; font-size: 13px; margin-bottom: 8px; }}
pre {{ white-space: pre-wrap; margin: 0; color: #efe2c7; font-size: 12px; }}
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


def _draw_message_bar(
    draw,
    state: dict[str, Any],
    events: dict[str, Any],
    x: int,
    y: int,
    w: int,
    h: int,
    title_font,
    font,
) -> None:
    draw.rounded_rectangle((x, y, x + w, y + h), radius=10, fill=PANEL, outline=(74, 60, 46))
    message = _message(state, events)
    draw.text((x + 14, y + 9), message[:96], fill=(244, 229, 182), font=title_font)
    subtitle = f"Round {state.get('round')}   Active {_active_role(state)}   Torch {state.get('torch')}   Alert {state.get('alert')}"
    draw.text((x + 14, y + 32), subtitle, fill=MUTED, font=font)


def _draw_board_backdrop(draw, x: int, y: int, w: int, h: int) -> None:
    draw.rounded_rectangle(
        (x - 6, y - 6, x + w + 6, y + h + 6), radius=12, fill=(19, 16, 14), outline=(91, 72, 49)
    )


def _paste_native(draw, box: tuple[int, int, int, int], painter) -> None:
    """Paint a 16x16 RGBA sprite into *box* using hard nearest scaling."""

    from PIL import Image, ImageDraw

    sprite = Image.new("RGBA", (NATIVE_TILE, NATIVE_TILE), (0, 0, 0, 0))
    sdraw = ImageDraw.Draw(sprite)
    painter(sdraw)
    x1, y1, x2, y2 = box
    size = (max(1, x2 - x1 + 1), max(1, y2 - y1 + 1))
    if size != sprite.size:
        try:
            resample = Image.Resampling.NEAREST
        except AttributeError:  # pragma: no cover - Pillow < 9.1
            resample = Image.NEAREST
        sprite = sprite.resize(size, resample)
    draw._image.paste(sprite, (x1, y1), sprite)


def _paint_floor(sprite, *, known: bool, alt: bool) -> None:
    if not known:
        sprite.rectangle((0, 0, 15, 15), fill=(23, 24, 25), outline=(32, 31, 30))
        return
    base = (70, 70, 66) if alt else (64, 64, 61)
    sprite.rectangle((0, 0, 15, 15), fill=base, outline=(36, 35, 34))
    sprite.line((0, 15, 15, 15), fill=(31, 31, 30))
    sprite.line((15, 0, 15, 15), fill=(31, 31, 30))
    sprite.line((0, 0, 15, 0), fill=(102, 98, 88))
    sprite.point((3, 4), fill=(95, 92, 84))
    sprite.point((11, 10), fill=(45, 44, 43))
    if alt:
        sprite.line((5, 2, 7, 4), fill=(43, 42, 41))
        sprite.point((8, 4), fill=(43, 42, 41))


def _paint_wall(sprite, *, known: bool) -> None:
    if not known:
        sprite.rectangle((0, 0, 15, 15), fill=(25, 27, 29), outline=(15, 15, 16))
        return
    sprite.rectangle((0, 0, 15, 15), fill=STONE, outline=OUTLINE)
    sprite.rectangle((1, 1, 7, 4), fill=STONE_LIGHT)
    sprite.rectangle((8, 1, 14, 4), fill=(103, 101, 93))
    sprite.rectangle((1, 5, 4, 9), fill=(70, 70, 66))
    sprite.rectangle((5, 5, 11, 9), fill=(99, 97, 90))
    sprite.rectangle((12, 5, 14, 9), fill=(63, 63, 60))
    sprite.rectangle((1, 10, 7, 14), fill=(56, 56, 54))
    sprite.rectangle((8, 10, 14, 14), fill=(73, 72, 68))
    sprite.line((0, 0, 15, 0), fill=(151, 137, 103))
    sprite.line((0, 15, 15, 15), fill=(30, 28, 26))


def _paint_marker(sprite, kind: str) -> None:
    if kind == "door":
        sprite.rectangle((5, 2, 11, 14), fill=WOOD_DARK, outline=OUTLINE)
        sprite.rectangle((6, 3, 10, 13), fill=WOOD)
        sprite.line((7, 3, 7, 13), fill=WOOD_LIGHT)
        sprite.point((10, 8), fill=GOLD)
    elif kind == "open_door":
        sprite.rectangle((4, 2, 7, 14), fill=WOOD_DARK, outline=OUTLINE)
        sprite.polygon([(8, 3), (13, 5), (13, 13), (8, 14)], fill=(42, 33, 27), outline=OUTLINE)
    elif kind == "chest":
        sprite.rectangle((3, 7, 13, 13), fill=WOOD, outline=OUTLINE)
        sprite.rectangle((4, 4, 12, 8), fill=WOOD_LIGHT, outline=OUTLINE)
        sprite.line((3, 8, 13, 8), fill=GOLD)
        sprite.rectangle((7, 8, 8, 11), fill=GOLD)
    elif kind == "trap":
        sprite.rectangle((3, 4, 12, 12), fill=(29, 28, 27), outline=OUTLINE)
        for x in (5, 8, 11):
            sprite.polygon([(x, 6), (x - 1, 11), (x + 1, 11)], fill=(185, 181, 163))
    elif kind == "objective":
        sprite.polygon([(8, 2), (13, 7), (8, 14), (3, 7)], fill=GOLD, outline=OUTLINE)
        sprite.rectangle((7, 6, 9, 9), fill=(128, 39, 47))
    elif kind == "stairs":
        sprite.rectangle((2, 2, 14, 14), fill=(27, 29, 31), outline=OUTLINE)
        for y in (4, 7, 10, 13):
            sprite.line((4, y, 13, y), fill=(119, 116, 106))
        sprite.rectangle((2, 2, 5, 14), fill=(17, 18, 19))
    elif kind == "exit":
        sprite.rectangle((2, 2, 14, 14), fill=(20, 30, 34), outline=BLUE)
        sprite.polygon(
            [(8, 3), (13, 8), (8, 13), (3, 8)], fill=(30, 73, 88), outline=(141, 209, 218)
        )


def _paint_furniture(sprite, category: str, destroyed: bool) -> None:
    if destroyed:
        sprite.line((4, 12, 12, 4), fill=WOOD_LIGHT)
        sprite.line((4, 4, 12, 12), fill=WOOD_DARK)
        return
    if category == "altar":
        sprite.rectangle((3, 7, 13, 12), fill=(87, 84, 80), outline=OUTLINE)
        sprite.rectangle((4, 5, 12, 7), fill=STONE_LIGHT, outline=OUTLINE)
        sprite.rectangle((7, 7, 8, 10), fill=GOLD)
        sprite.point((5, 4), fill=TORCH)
        sprite.point((11, 4), fill=TORCH)
    elif category == "signal":
        sprite.rectangle((7, 6, 8, 14), fill=(61, 47, 31), outline=OUTLINE)
        sprite.rectangle((5, 5, 10, 7), fill=(60, 46, 34), outline=OUTLINE)
        sprite.polygon([(8, 1), (5, 5), (8, 6), (11, 5)], fill=TORCH)
        sprite.point((8, 3), fill=(255, 217, 84))
    elif category == "lore":
        sprite.rectangle((3, 3, 13, 13), fill=WOOD_DARK, outline=OUTLINE)
        for x, color in [(5, BLUE), (7, GOLD), (9, GREEN), (11, BURGUNDY)]:
            sprite.rectangle((x, 5, x + 1, 11), fill=color)
    elif category == "supply":
        sprite.rectangle((4, 4, 12, 13), fill=WOOD, outline=OUTLINE)
        sprite.line((4, 6, 12, 6), fill=STONE_LIGHT)
        sprite.line((4, 11, 12, 11), fill=STONE_LIGHT)
        sprite.line((6, 4, 6, 13), fill=WOOD_LIGHT)
        sprite.line((10, 4, 10, 13), fill=WOOD_LIGHT)
    elif category == "treasure":
        sprite.rectangle((3, 8, 13, 13), fill=GOLD, outline=OUTLINE)
        sprite.point((6, 7), fill=(70, 132, 188))
        sprite.point((10, 7), fill=(196, 59, 55))
        sprite.rectangle((5, 5, 11, 9), fill=WOOD, outline=OUTLINE)
    elif category == "armory":
        sprite.rectangle((5, 3, 11, 13), fill=(64, 54, 43), outline=OUTLINE)
        sprite.line((7, 4, 7, 12), fill=BONE)
        sprite.line((10, 3, 10, 12), fill=STONE_LIGHT)
        sprite.point((10, 2), fill=STONE_LIGHT)
    elif category == "hazard":
        _paint_marker(sprite, "trap")
    else:
        sprite.rectangle((3, 6, 13, 10), fill=WOOD, outline=OUTLINE)
        sprite.rectangle((4, 10, 5, 13), fill=WOOD_DARK)
        sprite.rectangle((11, 10, 12, 13), fill=WOOD_DARK)
        sprite.line((4, 7, 12, 7), fill=WOOD_LIGHT)


def _paint_hero(sprite, role: str) -> None:
    if role == "wizard":
        sprite.line((12, 3, 12, 14), fill=WOOD_LIGHT)
        sprite.point((12, 2), fill=(95, 184, 220))
        sprite.polygon([(8, 1), (4, 6), (12, 6)], fill=BLUE, outline=OUTLINE)
        sprite.rectangle((5, 6, 11, 13), fill=BLUE, outline=OUTLINE)
        sprite.rectangle((6, 6, 10, 8), fill=(219, 178, 132))
        sprite.rectangle((6, 8, 10, 11), fill=BONE)
        sprite.line((8, 9, 8, 13), fill=GOLD)
    elif role == "elf":
        sprite.arc((10, 3, 15, 13), 90, 270, fill=WOOD_LIGHT)
        sprite.line((13, 4, 13, 12), fill=BONE)
        sprite.polygon([(8, 2), (3, 7), (13, 7)], fill=(52, 91, 48), outline=OUTLINE)
        sprite.rectangle((5, 7, 11, 13), fill=(61, 104, 50), outline=OUTLINE)
        sprite.rectangle((6, 6, 10, 9), fill=(160, 103, 61))
        sprite.rectangle((4, 9, 6, 12), fill=WOOD_DARK)
    elif role == "dwarf":
        sprite.rectangle((5, 6, 11, 13), fill=(219, 210, 178), outline=OUTLINE)
        sprite.rectangle((6, 3, 10, 7), fill=(226, 220, 201), outline=OUTLINE)
        sprite.rectangle((4, 8, 7, 12), fill=BLUE, outline=GOLD)
        sprite.line((12, 4, 12, 12), fill=GOLD)
        sprite.rectangle((11, 3, 13, 5), fill=GOLD)
        sprite.line((8, 7, 8, 12), fill=GOLD)
    elif role == "goblin_scout":
        sprite.line((12, 5, 14, 12), fill=WOOD_LIGHT)
        sprite.rectangle((5, 7, 11, 13), fill=(72, 58, 45), outline=OUTLINE)
        sprite.polygon([(8, 2), (3, 7), (13, 7)], fill=(58, 45, 68), outline=OUTLINE)
        sprite.rectangle((6, 5, 10, 8), fill=(104, 159, 67), outline=OUTLINE)
        sprite.polygon([(5, 6), (2, 5), (5, 7)], fill=(104, 159, 67), outline=OUTLINE)
        sprite.polygon([(11, 6), (14, 5), (11, 7)], fill=(104, 159, 67), outline=OUTLINE)
        sprite.point((7, 6), fill=GOLD)
        sprite.point((9, 6), fill=GOLD)
    elif role == "ogre_bruiser":
        sprite.rectangle((3, 7, 13, 14), fill=(92, 132, 58), outline=OUTLINE)
        sprite.rectangle((4, 3, 12, 9), fill=(104, 145, 66), outline=OUTLINE)
        sprite.rectangle((3, 8, 6, 10), fill=STONE_LIGHT)
        sprite.line((13, 3, 15, 13), fill=WOOD_LIGHT)
        sprite.rectangle((12, 2, 15, 4), fill=WOOD_DARK, outline=OUTLINE)
        sprite.point((6, 5), fill=OUTLINE)
        sprite.point((10, 5), fill=OUTLINE)
    elif role == "kobold_tinkerer":
        sprite.rectangle((5, 7, 11, 13), fill=(122, 79, 44), outline=OUTLINE)
        sprite.rectangle((5, 4, 11, 8), fill=(190, 83, 43), outline=OUTLINE)
        sprite.polygon([(5, 5), (2, 6), (5, 7)], fill=(190, 83, 43), outline=OUTLINE)
        sprite.line((12, 3, 12, 14), fill=STONE_LIGHT)
        sprite.line((10, 12, 14, 14), fill=(190, 83, 43))
        sprite.point((8, 6), fill=GOLD)
    elif role == "boggart_trickster":
        sprite.rectangle((5, 7, 11, 13), fill=(65, 49, 86), outline=OUTLINE)
        sprite.rectangle((6, 4, 10, 8), fill=(104, 129, 149), outline=OUTLINE)
        sprite.polygon([(5, 5), (1, 4), (5, 7)], fill=(82, 75, 124), outline=OUTLINE)
        sprite.polygon([(11, 5), (15, 4), (11, 7)], fill=(82, 75, 124), outline=OUTLINE)
        sprite.line((12, 3, 12, 14), fill=WOOD_LIGHT)
        sprite.arc((10, 2, 15, 7), 200, 40, fill=(183, 133, 220))
        sprite.point((7, 6), fill=GOLD)
        sprite.point((9, 6), fill=GOLD)
    elif role == "barbarian":
        sprite.line((3, 4, 3, 13), fill=BONE)
        sprite.rectangle((2, 3, 4, 4), fill=BONE)
        sprite.rectangle((6, 5, 10, 12), fill=(164, 164, 156), outline=OUTLINE)
        sprite.rectangle((6, 3, 10, 6), fill=(199, 199, 188), outline=OUTLINE)
        sprite.rectangle((10, 7, 13, 12), fill=BLUE, outline=GOLD)
        sprite.point((8, 5), fill=OUTLINE)
    else:
        sprite.rectangle((5, 6, 11, 13), fill=(88, 108, 132), outline=OUTLINE)
        sprite.rectangle((6, 3, 10, 7), fill=(206, 154, 107), outline=OUTLINE)


def _monster_family(role: str) -> str:
    if role in {"bone_guard", "hollow_knight"}:
        return "skeleton"
    if role in {"gloom_cultist"}:
        return "cultist"
    if role in {"crypt_brute"}:
        return "orc"
    if role in {"skitterling"}:
        return "spider"
    if role in {"rat_pack"}:
        return "rat_pack"
    if role in {"iron_sentinel", "hollow_knight"}:
        return "sentinel"
    return "goblin"


def _paint_monster(sprite, role: str) -> None:
    if role.startswith("dwarf_"):
        sprite.rectangle((4, 7, 12, 13), fill=(123, 96, 65), outline=OUTLINE)
        sprite.rectangle((5, 4, 11, 8), fill=(196, 144, 82), outline=OUTLINE)
        sprite.rectangle((5, 2, 11, 5), fill=STONE_LIGHT, outline=OUTLINE)
        sprite.rectangle((6, 8, 10, 11), fill=(82, 87, 91), outline=OUTLINE)
        sprite.point((7, 6), fill=OUTLINE)
        sprite.point((9, 6), fill=OUTLINE)
        if role == "dwarf_shieldbearer":
            sprite.rectangle((2, 8, 5, 13), fill=BLUE, outline=GOLD)
        elif role == "dwarf_crossbow":
            sprite.line((2, 7, 14, 7), fill=WOOD_LIGHT)
            sprite.line((8, 5, 8, 11), fill=WOOD_DARK)
        elif role == "dwarf_runekeeper":
            sprite.point((12, 4), fill=GOLD)
            sprite.line((12, 5, 12, 13), fill=GOLD)
        elif role == "dwarf_warden":
            sprite.rectangle((3, 8, 6, 13), fill=BURGUNDY, outline=GOLD)
            sprite.line((13, 4, 13, 13), fill=STONE_LIGHT)
        else:
            sprite.line((12, 5, 13, 13), fill=STONE_LIGHT)
        return
    if role == "cinder_mage":
        sprite.polygon([(8, 2), (3, 13), (13, 13)], fill=BURGUNDY, outline=OUTLINE)
        sprite.rectangle((6, 5, 10, 8), fill=(25, 18, 15))
        sprite.point((6, 7), fill=TORCH)
        sprite.point((10, 7), fill=TORCH)
        sprite.polygon([(12, 2), (10, 6), (13, 7), (14, 3)], fill=TORCH, outline=OUTLINE)
        sprite.point((12, 4), fill=(255, 219, 85))
        return
    if role == "mirror_adept":
        sprite.polygon(
            [(8, 1), (13, 6), (8, 15), (3, 6)], fill=(150, 194, 202), outline=(31, 75, 83)
        )
        sprite.polygon([(8, 3), (11, 6), (8, 12), (5, 6)], fill=(202, 232, 232))
        sprite.line((5, 5, 11, 11), fill=(246, 255, 255))
        sprite.line((10, 4, 6, 12), fill=(83, 145, 156))
        return
    if role == "lantern_wight":
        sprite.rectangle((6, 5, 10, 12), fill=(75, 153, 181), outline=OUTLINE)
        sprite.polygon([(8, 1), (4, 6), (12, 6)], fill=(105, 190, 208), outline=OUTLINE)
        sprite.rectangle((6, 6, 10, 8), fill=(18, 22, 23))
        sprite.point((6, 7), fill=GOLD)
        sprite.point((10, 7), fill=GOLD)
        sprite.rectangle((7, 10, 9, 13), fill=TORCH)
        return
    if role == "tusk_mauler":
        sprite.rectangle((3, 6, 13, 13), fill=(99, 140, 64), outline=OUTLINE)
        sprite.rectangle((4, 3, 12, 8), fill=(86, 130, 56), outline=OUTLINE)
        sprite.polygon([(4, 5), (0, 7), (4, 8)], fill=BONE, outline=OUTLINE)
        sprite.polygon([(12, 5), (15, 7), (12, 8)], fill=BONE, outline=OUTLINE)
        sprite.rectangle((5, 9, 7, 12), fill=STONE_LIGHT)
        sprite.line((13, 4, 15, 13), fill=STONE_LIGHT)
        sprite.point((6, 5), fill=OUTLINE)
        sprite.point((10, 5), fill=OUTLINE)
        return
    if role == "iron_sentinel":
        sprite.rectangle((4, 4, 12, 13), fill=(126, 132, 130), outline=OUTLINE)
        sprite.rectangle((5, 6, 11, 8), fill=(39, 47, 50))
        sprite.line((3, 10, 13, 10), fill=STONE_LIGHT)
        sprite.rectangle((6, 2, 10, 4), fill=(164, 166, 158), outline=OUTLINE)
        return
    if role == "hollow_knight":
        sprite.rectangle((5, 5, 11, 13), fill=(113, 113, 107), outline=OUTLINE)
        sprite.rectangle((6, 2, 10, 6), fill=BONE, outline=OUTLINE)
        sprite.rectangle((6, 7, 10, 10), fill=(54, 57, 58), outline=OUTLINE)
        sprite.point((7, 4), fill=OUTLINE)
        sprite.point((9, 4), fill=OUTLINE)
        sprite.line((12, 3, 12, 13), fill=BONE)
        return
    family = _monster_family(role)
    if family == "skeleton":
        sprite.rectangle((7, 3, 9, 12), fill=BONE)
        sprite.rectangle((5, 2, 11, 7), fill=BONE, outline=OUTLINE)
        sprite.rectangle((5, 9, 11, 10), fill=BONE)
        sprite.line((4, 6, 2, 12), fill=BONE)
        sprite.line((12, 6, 14, 12), fill=BONE)
        sprite.point((7, 5), fill=OUTLINE)
        sprite.point((9, 5), fill=OUTLINE)
        sprite.line((12, 3, 12, 13), fill=(185, 181, 163))
    elif family == "cultist":
        sprite.polygon([(8, 2), (3, 13), (13, 13)], fill=BURGUNDY, outline=OUTLINE)
        sprite.rectangle((6, 5, 10, 8), fill=(20, 18, 16))
        sprite.point((6, 7), fill=GOLD)
        sprite.point((10, 7), fill=GOLD)
        sprite.line((8, 9, 8, 12), fill=GOLD)
    elif family == "orc":
        sprite.rectangle((4, 6, 12, 13), fill=(82, 124, 56), outline=OUTLINE)
        sprite.rectangle((5, 3, 11, 8), fill=GREEN, outline=OUTLINE)
        sprite.rectangle((4, 8, 6, 10), fill=STONE_LIGHT)
        sprite.rectangle((10, 8, 12, 10), fill=STONE_LIGHT)
        sprite.line((13, 5, 14, 13), fill=STONE_LIGHT)
        sprite.point((6, 5), fill=OUTLINE)
        sprite.point((10, 5), fill=OUTLINE)
    elif family == "spider":
        sprite.rectangle((5, 5, 11, 11), fill=(45, 35, 32), outline=OUTLINE)
        sprite.rectangle((6, 3, 10, 6), fill=(59, 43, 37), outline=OUTLINE)
        for y in (5, 7, 9):
            sprite.line((5, y, 1, y - 2), fill=OUTLINE)
            sprite.line((11, y, 15, y - 2), fill=OUTLINE)
        sprite.point((7, 7), fill=RED)
        sprite.point((9, 7), fill=RED)
    elif family == "rat_pack":
        for ox, oy in ((4, 7), (8, 5), (11, 9)):
            sprite.rectangle((ox - 2, oy - 1, ox + 2, oy + 2), fill=(104, 91, 67), outline=OUTLINE)
            sprite.point((ox + 1, oy), fill=OUTLINE)
    elif family == "sentinel":
        sprite.rectangle((4, 4, 12, 13), fill=(136, 138, 132), outline=OUTLINE)
        sprite.rectangle((5, 6, 11, 8), fill=(49, 55, 60))
        sprite.line((3, 10, 13, 10), fill=STONE_LIGHT)
    else:
        sprite.rectangle((4, 7, 12, 13), fill=GREEN, outline=OUTLINE)
        sprite.rectangle((5, 4, 11, 9), fill=(102, 159, 67), outline=OUTLINE)
        sprite.polygon([(5, 5), (2, 6), (5, 7)], fill=GREEN, outline=OUTLINE)
        sprite.polygon([(11, 5), (14, 6), (11, 7)], fill=GREEN, outline=OUTLINE)
        sprite.line((12, 6, 14, 13), fill=BONE)
        sprite.point((6, 6), fill=OUTLINE)
        sprite.point((10, 6), fill=OUTLINE)


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
                draw.rectangle(box, fill=VOID)
            else:
                _draw_floor(draw, box, known_tile, (x + y) % 2 == 0)


def _draw_floor(draw, box: tuple[int, int, int, int], known: bool, alt: bool) -> None:
    _paste_native(draw, box, lambda sprite: _paint_floor(sprite, known=known, alt=alt))


def _draw_wall(draw, box: tuple[int, int, int, int], known: bool) -> None:
    _paste_native(draw, box, lambda sprite: _paint_wall(sprite, known=known))


def _draw_statics(draw, state: dict[str, Any], x0: int, y0: int, tile: int) -> None:
    known = _known_tiles(state)
    party_visible = state.get("visibility") not in {"omniscient", "private", "warden"}
    visible = None if not party_visible else known
    _draw_marker(draw, state.get("entry"), x0, y0, tile, "stairs", visible)
    _draw_marker(draw, state.get("escape_tile"), x0, y0, tile, "exit", visible)
    for door in (state.get("doors") or {}).values():
        if door.get("secret") and not door.get("discovered"):
            continue
        _draw_marker(
            draw,
            door.get("pos"),
            x0,
            y0,
            tile,
            "open_door" if door.get("state") == "open" else "door",
            visible,
        )
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


def _draw_marker(
    draw, pos: Any, x0: int, y0: int, tile: int, kind: str, visible: set[tuple[int, int]] | None
) -> None:
    parsed = _pos(pos)
    if parsed is None:
        return
    x, y = parsed
    if visible is not None and (x, y) not in visible:
        return
    box = _tile_box(x0, y0, x, y, tile)
    _paste_native(draw, box, lambda sprite: _paint_marker(sprite, kind))


def _draw_furniture(
    draw,
    furniture: dict[str, Any],
    x0: int,
    y0: int,
    tile: int,
    visible: set[tuple[int, int]] | None,
) -> None:
    pos = _pos(furniture.get("pos"))
    if pos is None:
        return
    if visible is not None and pos not in visible:
        return
    box = _tile_box(x0, y0, pos[0], pos[1], tile)
    category = str(furniture.get("category") or "furniture")
    _paste_native(
        draw,
        box,
        lambda sprite: _paint_furniture(sprite, category, bool(furniture.get("destroyed"))),
    )
    if furniture.get("destructible"):
        x1, y1, _x2, _y2 = box
        hp = max(0, int(furniture.get("hp", 1)))
        max_hp = max(1, int(furniture.get("max_hp", hp or 1)))
        if hp < max_hp:
            _draw_hp_bar(draw, x1 + 4, y1 + 2, tile - 8, 3, hp, max_hp)


def _draw_entities(draw, state: dict[str, Any], x0: int, y0: int, tile: int, font) -> None:
    known = _known_tiles(state)
    party_visible = state.get("visibility") not in {"omniscient", "private", "warden"}
    visible = None if not party_visible else known
    active = state.get("active_agent")
    for monster in (state.get("monsters") or {}).values():
        pos = _pos(monster.get("pos"))
        if pos is None or (visible is not None and pos not in visible):
            continue
        if monster.get("alive", True):
            _draw_monster(draw, monster, pos, x0, y0, tile)
        elif "knocked_out" in (monster.get("status") or []):
            _draw_knocked_out(draw, monster, pos, x0, y0, tile)
    for hero in (state.get("heroes") or {}).values():
        if hero.get("alive", True):
            pos = _pos(hero.get("pos"))
            if pos is not None:
                _draw_hero(draw, hero, pos, x0, y0, tile, font, active=hero.get("id") == active)


def _draw_action_trails(
    draw, state: dict[str, Any], events: dict[str, Any], x0: int, y0: int, tile: int
) -> None:
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


def _draw_footprints(
    draw, hero: dict[str, Any], pos: tuple[int, int], x0: int, y0: int, tile: int, direction: str
) -> None:
    role = str(hero.get("role") or "")
    color = {
        "barbarian": (198, 82, 72),
        "wizard": (130, 102, 222),
        "elf": (80, 172, 104),
        "dwarf": (210, 143, 64),
        "goblin_scout": (104, 159, 67),
        "ogre_bruiser": (92, 132, 58),
        "kobold_tinkerer": (190, 83, 43),
        "boggart_trickster": (183, 133, 220),
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


def _draw_hero(
    draw,
    hero: dict[str, Any],
    pos: tuple[int, int],
    x0: int,
    y0: int,
    tile: int,
    font,
    active: bool,
) -> None:
    role = str(hero.get("role") or "hero")
    x, y = pos
    box = _tile_box(x0, y0, x, y, tile)
    x1, y1, x2, y2 = box
    if active:
        draw.rectangle((x1 + 1, y1 + 1, x2 - 1, y2 - 1), outline=(255, 221, 116), width=2)
    _paste_native(draw, box, lambda sprite: _paint_hero(sprite, role))
    _draw_equipment_marks(draw, hero, box)
    _draw_hp_bar(draw, x1 + 4, y1 + 2, tile - 8, 3, hero.get("hp", 0), hero.get("max_hp", 1))


def _draw_equipment_marks(draw, hero: dict[str, Any], box: tuple[int, int, int, int]) -> None:
    # Subtle pixel overlays only; base silhouettes should carry the class read.
    equipment = hero.get("equipment") or {}
    x1, y1, x2, _y2 = box
    tile = x2 - x1 + 1
    scale = max(1, tile // NATIVE_TILE)
    if equipment.get("offhand") == "shield":
        draw.rectangle(
            (x1 + 2 * scale, y1 + 8 * scale, x1 + 4 * scale, y1 + 12 * scale),
            fill=BLUE,
            outline=GOLD,
        )
    if equipment.get("cloak") == "warding_cloak":
        draw.line(
            (x1 + 4 * scale, y1 + 4 * scale, x1 + 12 * scale, y1 + 4 * scale),
            fill=(96, 174, 190),
            width=max(1, scale),
        )
    if equipment.get("helm") == "iron_helm":
        draw.rectangle(
            (x1 + 6 * scale, y1 + 2 * scale, x1 + 10 * scale, y1 + 4 * scale), fill=STONE_LIGHT
        )
    if equipment.get("charm") == "holy_charm":
        draw.rectangle(
            (x1 + 11 * scale, y1 + 4 * scale, x1 + 12 * scale, y1 + 5 * scale), fill=GOLD
        )


def _draw_barbarian(draw, cx: int, cy: int) -> None:
    # Compatibility shim for third-party code that may call the old private helper.
    _paste_native(
        draw, (cx - 16, cy - 16, cx + 15, cy + 15), lambda sprite: _paint_hero(sprite, "barbarian")
    )


def _draw_wizard(draw, cx: int, cy: int) -> None:
    _paste_native(
        draw, (cx - 16, cy - 16, cx + 15, cy + 15), lambda sprite: _paint_hero(sprite, "wizard")
    )


def _draw_elf(draw, cx: int, cy: int) -> None:
    _paste_native(
        draw, (cx - 16, cy - 16, cx + 15, cy + 15), lambda sprite: _paint_hero(sprite, "elf")
    )


def _draw_dwarf(draw, cx: int, cy: int) -> None:
    _paste_native(
        draw, (cx - 16, cy - 16, cx + 15, cy + 15), lambda sprite: _paint_hero(sprite, "dwarf")
    )


def _draw_adventurer(draw, cx: int, cy: int) -> None:
    _paste_native(
        draw, (cx - 16, cy - 16, cx + 15, cy + 15), lambda sprite: _paint_hero(sprite, "hero")
    )


def _draw_face(draw, cx: int, cy: int) -> None:
    draw.rectangle((cx - 1, cy, cx, cy + 1), fill=OUTLINE)
    draw.rectangle((cx + 3, cy, cx + 4, cy + 1), fill=OUTLINE)


def _draw_monster(
    draw, monster: dict[str, Any], pos: tuple[int, int], x0: int, y0: int, tile: int
) -> None:
    role = str(monster.get("role") or "monster")
    x, y = pos
    box = _tile_box(x0, y0, x, y, tile)
    x1, y1, _x2, _y2 = box
    _paste_native(draw, box, lambda sprite: _paint_monster(sprite, role))
    _draw_hp_bar(
        draw,
        x1 + 5,
        y1 + 2,
        tile - 10,
        3,
        monster.get("hp", 1),
        monster.get("max_hp", monster.get("hp", 1)),
    )


def _draw_knocked_out(
    draw, monster: dict[str, Any], pos: tuple[int, int], x0: int, y0: int, tile: int
) -> None:
    role = str(monster.get("role") or "monster")
    x, y = pos
    box = _tile_box(x0, y0, x, y, tile)
    x1, y1, x2, _y2 = box
    _paste_native(draw, box, lambda sprite: _paint_monster(sprite, role))
    scale = max(1, tile // NATIVE_TILE)
    # Dim/prone marker plus sleep stars: visible as knockout, not corpse.
    draw.rectangle(
        (x1 + 3 * scale, y1 + 9 * scale, x2 - 3 * scale, y1 + 13 * scale),
        fill=(36, 32, 29),
        outline=OUTLINE,
    )
    for ox, oy in ((10, 3), (12, 5), (9, 6)):
        draw.text((x1 + ox * scale, y1 + oy * scale), "z", fill=GOLD)


def _draw_hp_bar(draw, x: int, y: int, w: int, h: int, hp: Any, max_hp: Any) -> None:
    try:
        hp_f = max(0.0, float(hp))
        max_f = max(1.0, float(max_hp))
    except (TypeError, ValueError):
        hp_f, max_f = 1.0, 1.0
    draw.rectangle((x, y, x + w, y + h), fill=(30, 20, 18))
    fill_w = int(w * min(1.0, hp_f / max_f))
    color = RED if hp_f / max_f < 0.4 else (88, 158, 76)
    draw.rectangle((x, y, x + fill_w, y + h), fill=color)
    draw.line((x, y, x + w, y), fill=(82, 63, 45))


def _draw_hud(
    draw,
    state: dict[str, Any],
    events: dict[str, Any],
    x: int,
    y: int,
    w: int,
    h: int,
    title_font,
    font,
    small,
) -> None:
    draw.rounded_rectangle((x, y, x + w, y + h), radius=12, fill=PANEL, outline=(74, 60, 46))
    yy = y + 14
    draw.text(
        (x + 14, yy),
        str(state.get("title") or state.get("quest_id") or "DungeonGrid")[:26],
        fill=TEXT,
        font=title_font,
    )
    yy += 32
    objective = state.get("objective") or {}
    active = state.get("active_agent")
    movement = (state.get("movement_remaining") or {}).get(active, "-")
    major = (state.get("major_action_used") or {}).get(active, False)
    lines = [
        f"Objective: {objective.get('id', '-')}",
        f"Carrier: {objective.get('carrier') or '-'}",
        f"Move: {movement}  Major: {'used' if major else 'ready'}",
        f"Dread: {state.get('dread', '-')}",
        f"Extracted: {len(state.get('extracted_heroes') or [])}",
        f"Reward this turn: {events.get('reward', 0)}",
        "",
        str((state.get("game_mode") or {}).get("party_label") or "Party").title(),
    ]
    for line in lines:
        draw.text(
            (x + 14, yy),
            line,
            fill=GOLD
            if line == str((state.get("game_mode") or {}).get("party_label") or "Party").title()
            else MUTED,
            font=font,
        )
        yy += 20
    for hero in (state.get("heroes") or {}).values():
        role = str(hero.get("role") or hero.get("id"))
        weapon = (hero.get("equipment") or {}).get("weapon", "-")
        draw.text(
            (x + 22, yy),
            f"{role:<9} HP {hero.get('hp')}/{hero.get('max_hp')}",
            fill=TEXT,
            font=font,
        )
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
            draw.text(
                (x + 22, yy),
                str(item.get("title") or item.get("id") or item)[:34],
                fill=TEXT,
                font=small,
            )
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
        return (
            f"DungeonGrid Sprite Replay: {state.get('title') or state.get('quest_id') or 'episode'}"
        )
    return "DungeonGrid Sprite Replay"


def _html_frame(frame: dict[str, Any], index: int) -> str:
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
