# Trial of Embers

## MARL purpose
Tests whether heroes time hazardous crossings and spend shared risk deliberately rather than independently.

## Tier coverage
- `pico`: A one-hero micro-probe that exposes the first hazard timing and shared risk budgeting decision without side branches.
- `lite`: A two-hero diagnostic focused on communication and first coordination failure modes for hazard timing and shared risk budgeting.
- `medium`: The legacy full task geometry, preserved as the canonical medium tier.
- `heavy`: A four-hero stress variant with additional lanes, side pressure, and stricter hazard timing and shared risk budgeting review signals.

## Recommended heroes by tier
- `pico`: 1 hero: Wizard.
- `lite`: 2 heroes: Barbarian + Wizard.
- `medium`: 3 heroes: Barbarian + Wizard + Dwarf.
- `heavy`: 4 heroes: Barbarian + Wizard + Elf + Dwarf.

## Quest IDs
- `pico`: `base:trial_of_embers:pico`
- `lite`: `base:trial_of_embers:lite`
- `medium`: `base:trial_of_embers:medium`
- `heavy`: `base:trial_of_embers:heavy`

## Success behaviors
- party waits for hazard checks before advancing
- carrier follows a marked route
- support uses guard/heal resources around unavoidable hazard timing

## Common failure modes
- heroes cross one at a time without sharing hazard info
- carrier takes the objective before traps are handled
- team burns time fighting while hazard budget rises

## Review signals in traces/replays
- trap searches/disarms before crossings
- hazard damage
- messages about safe timing
- carrier hazard exposure

## Coordination skills
- stage before crossing hazard lanes
- communicate when traps or ember pulses are safe/unsafe
- assign one hero to clear or mark hazards before the carrier moves

## Pressure sources
- traps
- ember pulses
- torch pressure
- monsters that force movement
