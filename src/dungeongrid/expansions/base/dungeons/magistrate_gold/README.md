# Magistrate Gold

## MARL purpose
Tests whether heroes preserve team success when optional gold creates individual temptation and shared risk.

## Tier coverage
- `pico`: A one-hero micro-probe that exposes the first mixed-motive social dilemma decision without side branches.
- `lite`: A two-hero diagnostic focused on communication and first coordination failure modes for mixed-motive social dilemma.
- `medium`: The legacy full task geometry, preserved as the canonical medium tier.
- `heavy`: A four-hero stress variant with additional lanes, side pressure, and stricter mixed-motive social dilemma review signals.

## Recommended heroes by tier
- `pico`: 1 hero: Wizard.
- `lite`: 2 heroes: Barbarian + Wizard.
- `medium`: 3 heroes: Barbarian + Wizard + Dwarf.
- `heavy`: 4 heroes: Barbarian + Wizard + Elf + Dwarf.

## Quest IDs
- `pico`: `base:magistrate_gold:pico`
- `lite`: `base:magistrate_gold:lite`
- `medium`: `base:magistrate_gold:medium`
- `heavy`: `base:magistrate_gold:heavy`

## Success behaviors
- party agrees on a treasure budget before opening side caches
- loot carriers still protect the objective carrier
- heroes abandon low-value gold when pressure rises

## Common failure modes
- one hero hoards tempo or consumables for private gain
- party opens every chest while monsters close on the exit
- no one communicates when greed changes the route plan

## Review signals in traces/replays
- treasure searches by hero
- items given
- objective delay after chest opens
- messages about risk

## Coordination skills
- negotiate when optional treasure is worth the tempo cost
- share healing and safety resources after risky searches
- stop searching once team extraction becomes the dominant objective

## Pressure sources
- optional chests
- greed-triggered threat
- shared torch/alert budget
- exit timing
