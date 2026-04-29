# Moonblade Vault

## MARL purpose
Tests whether the team sequences vault access, specialist actions, and optional treasure without breaking the main route.

## Tier coverage
- `pico`: A one-hero micro-probe that exposes the first specialist sequencing and greed control decision without side branches.
- `lite`: A two-hero diagnostic focused on communication and first coordination failure modes for specialist sequencing and greed control.
- `medium`: The legacy full task geometry, preserved as the canonical medium tier.
- `heavy`: A four-hero stress variant with additional lanes, side pressure, and stricter specialist sequencing and greed control review signals.

## Recommended heroes by tier
- `pico`: 1 hero: Wizard.
- `lite`: 2 heroes: Barbarian + Wizard.
- `medium`: 3 heroes: Barbarian + Wizard + Dwarf.
- `heavy`: 4 heroes: Barbarian + Wizard + Elf + Dwarf.

## Quest IDs
- `pico`: `base:moonblade_vault:pico`
- `lite`: `base:moonblade_vault:lite`
- `medium`: `base:moonblade_vault:medium`
- `heavy`: `base:moonblade_vault:heavy`

## Success behaviors
- dwarf or scout checks the vault path before pickup
- party agrees which treasure is skipped
- objective carrier has an escort before leaving the vault

## Common failure modes
- non-specialist triggers vault hazards prematurely
- loot branches consume the extraction window
- moonblade carrier becomes isolated

## Review signals in traces/replays
- specialist actions before vault open
- treasure detours
- carrier protection
- messages before cache interactions

## Coordination skills
- wait for the specialist before opening vault hazards
- announce optional loot before taking it
- protect the key or blade carrier on exit

## Pressure sources
- vault locks
- secret routes
- optional treasure
- carrier pursuit
