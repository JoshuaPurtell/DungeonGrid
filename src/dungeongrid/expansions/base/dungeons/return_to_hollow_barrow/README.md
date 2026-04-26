# Return to Hollow Barrow

## MARL purpose
Tests whether teams use remembered structure while adapting to changed pressure in a revisited dungeon.

## Tier coverage
- `pico`: A one-hero micro-probe that exposes the first long-horizon memory and adaptation decision without side branches.
- `lite`: A two-hero diagnostic focused on communication and first coordination failure modes for long-horizon memory and adaptation.
- `medium`: The legacy full task geometry, preserved as the canonical medium tier.
- `heavy`: A four-hero stress variant with additional lanes, side pressure, and stricter long-horizon memory and adaptation review signals.

## Recommended heroes by tier
- `pico`: 1 hero: Wizard.
- `lite`: 2 heroes: Barbarian + Wizard.
- `medium`: 3 heroes: Barbarian + Wizard + Dwarf.
- `heavy`: 4 heroes: Barbarian + Wizard + Elf + Dwarf.

## Quest IDs
- `pico`: `base:return_to_hollow_barrow:pico`
- `lite`: `base:return_to_hollow_barrow:lite`
- `medium`: `base:return_to_hollow_barrow:medium`
- `heavy`: `base:return_to_hollow_barrow:heavy`

## Success behaviors
- party references known landmarks but checks for changes
- scout confirms the old shortcut before the carrier commits
- team updates the plan when a remembered path is blocked

## Common failure modes
- heroes follow the old plan after new evidence contradicts it
- changed pressure is not communicated
- familiar loot rooms distract from the changed objective path

## Review signals in traces/replays
- route-name reuse
- verification before entry
- wrong assumptions about changed rooms
- adaptive replans

## Coordination skills
- reuse prior route labels in messages
- verify changed rooms before assuming old safety
- adapt the extraction plan when familiar lanes shift

## Pressure sources
- changed familiar routes
- hollow guards
- secret return paths
- boss remnant
