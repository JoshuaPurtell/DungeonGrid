# Veiled Castle

## MARL purpose
Tests whether heroes coordinate quiet movement, scouting, and detection risk under castle patrol pressure.

## Tier coverage
- `pico`: A one-hero micro-probe that exposes the first stealth coordination and detection management decision without side branches.
- `lite`: A two-hero diagnostic focused on communication and first coordination failure modes for stealth coordination and detection management.
- `medium`: The legacy full task geometry, preserved as the canonical medium tier.
- `heavy`: A four-hero stress variant with additional lanes, side pressure, and stricter stealth coordination and detection management review signals.

## Recommended heroes by tier
- `pico`: 1 hero: Wizard.
- `lite`: 2 heroes: Barbarian + Wizard.
- `medium`: 3 heroes: Barbarian + Wizard + Dwarf.
- `heavy`: 4 heroes: Barbarian + Wizard + Elf + Dwarf.

## Quest IDs
- `pico`: `base:veiled_castle:pico`
- `lite`: `base:veiled_castle:lite`
- `medium`: `base:veiled_castle:medium`
- `heavy`: `base:veiled_castle:heavy`

## Success behaviors
- scout marks safe lanes before the party advances
- heroes avoid unnecessary noise near patrols
- party has a fallback plan when detection occurs

## Common failure modes
- frontline opens loud doors before scout confirmation
- stealth break causes unplanned scattering
- optional loot triggers alarm with no warning

## Review signals in traces/replays
- alert increments
- messages before noisy actions
- scout-before-group moves
- regroup after detection

## Coordination skills
- announce noisy actions before taking them
- let scouts verify patrol lanes before group movement
- coordinate regroup points after stealth breaks

## Pressure sources
- patrol sight lines
- secret doors
- alarm cultists
- optional noisy loot
