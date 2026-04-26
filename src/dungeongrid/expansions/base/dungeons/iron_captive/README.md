# Iron Captive

## MARL purpose
Tests escort discipline: scouting, body-blocking, and threat control around a fragile captive or carrier.

## Tier coverage
- `pico`: A one-hero micro-probe that exposes the first escort/protection decision without side branches.
- `lite`: A two-hero diagnostic focused on communication and first coordination failure modes for escort/protection.
- `medium`: The legacy full task geometry, preserved as the canonical medium tier.
- `heavy`: A four-hero stress variant with additional lanes, side pressure, and stricter escort/protection review signals.

## Recommended heroes by tier
- `pico`: 1 hero: Wizard.
- `lite`: 2 heroes: Barbarian + Wizard.
- `medium`: 3 heroes: Barbarian + Wizard + Dwarf.
- `heavy`: 4 heroes: Barbarian + Wizard + Elf + Dwarf.

## Quest IDs
- `pico`: `base:iron_captive:pico`
- `lite`: `base:iron_captive:lite`
- `medium`: `base:iron_captive:medium`
- `heavy`: `base:iron_captive:heavy`

## Success behaviors
- frontliner opens a lane before the carrier advances
- support heroes stay adjacent enough to heal or body-block
- party clears ranged or fast threats before moving the captive

## Common failure modes
- carrier runs ahead of protection
- frontline chases loot and leaves the captive exposed
- heroes block their own extraction corridor

## Review signals in traces/replays
- guard actions near carrier
- distance from escort to carrier
- damage absorbed before carrier
- unsafe carrier moves

## Coordination skills
- assign scout, escort, and rear-guard roles
- body-block enemies without trapping the escorted unit
- time objective movement with lane control

## Pressure sources
- fragile objective
- intercepting guards
- narrow corridors
- rear pursuit
