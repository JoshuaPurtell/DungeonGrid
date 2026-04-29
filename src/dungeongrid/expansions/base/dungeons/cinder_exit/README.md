# Cinder Exit

## MARL purpose
Tests whether the team can switch from exploration to exit execution while pressure pursues the carrier.

## Tier coverage
- `pico`: A one-hero micro-probe that exposes the first extraction under pursuit decision without side branches.
- `lite`: A two-hero diagnostic focused on communication and first coordination failure modes for extraction under pursuit.
- `medium`: The legacy full task geometry, preserved as the canonical medium tier.
- `heavy`: A four-hero stress variant with additional lanes, side pressure, and stricter extraction under pursuit review signals.

## Recommended heroes by tier
- `pico`: 1 hero: Wizard.
- `lite`: 2 heroes: Barbarian + Wizard.
- `medium`: 3 heroes: Barbarian + Wizard + Dwarf.
- `heavy`: 4 heroes: Barbarian + Wizard + Elf + Dwarf.

## Quest IDs
- `pico`: `base:cinder_exit:pico`
- `lite`: `base:cinder_exit:lite`
- `medium`: `base:cinder_exit:medium`
- `heavy`: `base:cinder_exit:heavy`

## Success behaviors
- route is cleared or marked before pickup
- carrier waits for escort rather than sprinting blind
- rear guard slows pursuit while others move toward exit

## Common failure modes
- party keeps exploring after the objective is hot
- carrier separates from support
- doorways are left open for pursuers without a blocker

## Review signals in traces/replays
- rounds from objective taken to escape
- carrier protection actions
- doors controlled on return
- unused actions after reveal stop

## Coordination skills
- pre-plan the return route before taking the objective
- hand off or escort the carrier under pursuit
- use guards, doors, and messages to maintain extraction tempo

## Pressure sources
- pursuit spawn
- long return path
- door choke points
- partial extraction risk
