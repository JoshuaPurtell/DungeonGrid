# Broken Oath Ambush

## MARL purpose
Tests rapid regrouping, threat calls, and support under surprise pressure.

## Tier coverage
- `pico`: A one-hero micro-probe that exposes the first ambush recovery and mutual support decision without side branches.
- `lite`: A two-hero diagnostic focused on communication and first coordination failure modes for ambush recovery and mutual support.
- `medium`: The legacy full task geometry, preserved as the canonical medium tier.
- `heavy`: A four-hero stress variant with additional lanes, side pressure, and stricter ambush recovery and mutual support review signals.

## Recommended heroes by tier
- `pico`: 1 hero: Wizard.
- `lite`: 2 heroes: Barbarian + Wizard.
- `medium`: 3 heroes: Barbarian + Wizard + Dwarf.
- `heavy`: 4 heroes: Barbarian + Wizard + Elf + Dwarf.

## Quest IDs
- `pico`: `base:broken_oath_ambush:pico`
- `lite`: `base:broken_oath_ambush:lite`
- `medium`: `base:broken_oath_ambush:medium`
- `heavy`: `base:broken_oath_ambush:heavy`

## Success behaviors
- heroes broadcast the first ambush reveal
- frontline moves to protect the most exposed teammate
- party retreats or pivots instead of scattering further

## Common failure modes
- each hero fights a separate local battle
- support arrives after the isolated hero is down
- ambush direction is never communicated

## Review signals in traces/replays
- rounds isolated after ambush
- messages on reveal
- rescue/guard actions
- damage before regroup

## Coordination skills
- call ambush direction immediately
- collapse isolated heroes toward a defensible lane
- prioritize rescue over private damage turns

## Pressure sources
- surprise flankers
- split starts
- cultist alarms
- short time-to-contact
