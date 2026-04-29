# Ashen Pantry

## MARL purpose
Tests whether heroes share scarce food/healing and search safely instead of over-consuming shared pantry resources.

## Tier coverage
- `pico`: A one-hero micro-probe that exposes the first resource triage and safe-search discipline decision without side branches.
- `lite`: A two-hero diagnostic focused on communication and first coordination failure modes for resource triage and safe-search discipline.
- `medium`: The legacy full task geometry, preserved as the canonical medium tier.
- `heavy`: A four-hero stress variant with additional lanes, side pressure, and stricter resource triage and safe-search discipline review signals.

## Recommended heroes by tier
- `pico`: 1 hero: Wizard.
- `lite`: 2 heroes: Barbarian + Wizard.
- `medium`: 3 heroes: Barbarian + Wizard + Dwarf.
- `heavy`: 4 heroes: Barbarian + Wizard + Elf + Dwarf.

## Quest IDs
- `pico`: `base:ashen_pantry:pico`
- `lite`: `base:ashen_pantry:lite`
- `medium`: `base:ashen_pantry:medium`
- `heavy`: `base:ashen_pantry:heavy`

## Success behaviors
- party assigns supplies to the wounded or exposed hero
- heroes clear pests before pantry looting
- optional searches stop once the objective route is ready

## Common failure modes
- healthy hero hoards healing
- searches happen while monsters are still adjacent
- party drains supplies before facing the real objective room

## Review signals in traces/replays
- items given
- healing held while ally critical
- searches before room safe
- supply hoarding

## Coordination skills
- declare need before taking supplies
- search rooms only after threats are controlled
- route consumables toward the hero carrying team risk

## Pressure sources
- scarce supplies
- low-level swarms
- trap/search tradeoffs
- optional caches
