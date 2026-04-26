# Barrow of the Hollow King

## MARL purpose
Tests whether the team discovers boss counterplay and prevents revived guards from overwhelming the route.

## Tier coverage
- `pico`: A one-hero micro-probe that exposes the first boss counterplay and revive control decision without side branches.
- `lite`: A two-hero diagnostic focused on communication and first coordination failure modes for boss counterplay and revive control.
- `medium`: The legacy full task geometry, preserved as the canonical medium tier.
- `heavy`: A four-hero stress variant with additional lanes, side pressure, and stricter boss counterplay and revive control review signals.

## Recommended heroes by tier
- `pico`: 1 hero: Wizard.
- `lite`: 2 heroes: Barbarian + Wizard.
- `medium`: 3 heroes: Barbarian + Wizard + Dwarf.
- `heavy`: 4 heroes: Barbarian + Wizard + Elf + Dwarf.

## Quest IDs
- `pico`: `base:barrow_of_the_hollow_king:pico`
- `lite`: `base:barrow_of_the_hollow_king:lite`
- `medium`: `base:barrow_of_the_hollow_king:medium`
- `heavy`: `base:barrow_of_the_hollow_king:heavy`

## Success behaviors
- party searches clues before committing heavy attacks
- frontline pins revived guards away from supports
- objective carrier waits for boss counterplay to be resolved

## Common failure modes
- boss is attacked blindly before clues are read
- guards are ignored until the exit is blocked
- the party splits during the boss phase without a plan

## Review signals in traces/replays
- counterplay searched before boss damage
- revived guards defeated
- route control during boss fight
- messages about boss rules

## Coordination skills
- search for counterplay before brute-force boss damage
- assign guard cleanup while boss pressure is active
- coordinate retreat when revive pressure exceeds tempo

## Pressure sources
- hollow knights
- boss chamber
- revive pressure
- secret or altar counterplay
