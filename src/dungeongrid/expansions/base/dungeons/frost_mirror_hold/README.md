# Frost Mirror Hold

## MARL purpose
Tests whether heroes coordinate observations to distinguish real threats and objectives from mirrored decoys.

## Tier coverage
- `pico`: A one-hero micro-probe that exposes the first decoy discrimination and role confirmation decision without side branches.
- `lite`: A two-hero diagnostic focused on communication and first coordination failure modes for decoy discrimination and role confirmation.
- `medium`: The legacy full task geometry, preserved as the canonical medium tier.
- `heavy`: A four-hero stress variant with additional lanes, side pressure, and stricter decoy discrimination and role confirmation review signals.

## Recommended heroes by tier
- `pico`: 1 hero: Wizard.
- `lite`: 2 heroes: Barbarian + Wizard.
- `medium`: 3 heroes: Barbarian + Wizard + Dwarf.
- `heavy`: 4 heroes: Barbarian + Wizard + Elf + Dwarf.

## Quest IDs
- `pico`: `base:frost_mirror_hold:pico`
- `lite`: `base:frost_mirror_hold:lite`
- `medium`: `base:frost_mirror_hold:medium`
- `heavy`: `base:frost_mirror_hold:heavy`

## Success behaviors
- heroes ask for confirmation before committing to a mirrored target
- scout reports decoy state and safe route
- party keeps enough formation to recover from deception

## Common failure modes
- first visible target is assumed to be the real objective
- heroes split too far while validating mirrors
- support resources are spent on false pressure

## Review signals in traces/replays
- verification messages
- attacks on decoys
- wrong-lane commitment
- resource use before confirmation

## Coordination skills
- compare observations before attacking or opening
- assign one scout to verify mirror rooms
- hold resources until target identity is confirmed

## Pressure sources
- mirror adepts
- decoy lanes
- split observation
- cold tempo pressure
