# Hourglass Escape

## MARL purpose
Tests shared temporal planning when every detour consumes scarce time before extraction.

## Tier coverage
- `pico`: A one-hero micro-probe that exposes the first deadline-aware planning decision without side branches.
- `lite`: A two-hero diagnostic focused on communication and first coordination failure modes for deadline-aware planning.
- `medium`: The legacy full task geometry, preserved as the canonical medium tier.
- `heavy`: A four-hero stress variant with additional lanes, side pressure, and stricter deadline-aware planning review signals.

## Recommended heroes by tier
- `pico`: 1 hero: Wizard.
- `lite`: 2 heroes: Barbarian + Wizard.
- `medium`: 3 heroes: Barbarian + Wizard + Dwarf.
- `heavy`: 4 heroes: Barbarian + Wizard + Elf + Dwarf.

## Quest IDs
- `pico`: `base:hourglass_escape:pico`
- `lite`: `base:hourglass_escape:lite`
- `medium`: `base:hourglass_escape:medium`
- `heavy`: `base:hourglass_escape:heavy`

## Success behaviors
- party counts turns before opening optional rooms
- heroes pre-position for extraction
- objective pickup happens only after the exit route is viable

## Common failure modes
- agents explore because local room reward is visible despite deadline
- pickup happens before the return path is clear
- no one announces the point of no return

## Review signals in traces/replays
- turns to objective
- turns objective-to-exit
- optional actions after deadline warnings
- messages about remaining time

## Coordination skills
- state deadline and remaining route length
- prune optional actions when schedule is tight
- stage heroes near exit before final pickup

## Pressure sources
- turn clock
- long return path
- optional branches
- pursuit after pickup
