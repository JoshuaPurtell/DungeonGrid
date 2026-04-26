# Tusk Warlord Lair

## MARL purpose
Tests spacing, lane assignment, and anti-cleave formation against heavy melee pressure.

## Tier coverage
- `pico`: A one-hero micro-probe that exposes the first formation control decision without side branches.
- `lite`: A two-hero diagnostic focused on communication and first coordination failure modes for formation control.
- `medium`: The legacy full task geometry, preserved as the canonical medium tier.
- `heavy`: A four-hero stress variant with additional lanes, side pressure, and stricter formation control review signals.

## Recommended heroes by tier
- `pico`: 1 hero: Wizard.
- `lite`: 2 heroes: Barbarian + Wizard.
- `medium`: 3 heroes: Barbarian + Wizard + Dwarf.
- `heavy`: 4 heroes: Barbarian + Wizard + Elf + Dwarf.

## Quest IDs
- `pico`: `base:tusk_warlord_lair:pico`
- `lite`: `base:tusk_warlord_lair:lite`
- `medium`: `base:tusk_warlord_lair:medium`
- `heavy`: `base:tusk_warlord_lair:heavy`

## Success behaviors
- barbarian or dwarf anchors the lane while ranged heroes support
- party avoids ending multiple heroes adjacent to a mauler
- injured blockers call for swaps before collapse

## Common failure modes
- everyone crowds into the same doorway
- ranged heroes step into melee lanes unnecessarily
- frontline never rotates and gets downed in place

## Review signals in traces/replays
- clustered hero turns
- frontline rotations
- damage taken by backline
- doorway hold turns

## Coordination skills
- maintain frontline/backline spacing
- rotate injured blockers out of choke points
- focus tusk threats without bunching in cleave lanes

## Pressure sources
- cleave monsters
- narrow lanes
- side pressure
- boss guard
