# Lost Apprentice

## MARL purpose
Tests coordinated search over uncertain rooms while preserving enough safety to rescue the target.

## Tier coverage
- `pico`: A one-hero micro-probe that exposes the first rescue search and information sharing decision without side branches.
- `lite`: A two-hero diagnostic focused on communication and first coordination failure modes for rescue search and information sharing.
- `medium`: The legacy full task geometry, preserved as the canonical medium tier.
- `heavy`: A four-hero stress variant with additional lanes, side pressure, and stricter rescue search and information sharing review signals.

## Recommended heroes by tier
- `pico`: 1 hero: Wizard.
- `lite`: 2 heroes: Barbarian + Wizard.
- `medium`: 3 heroes: Barbarian + Wizard + Dwarf.
- `heavy`: 4 heroes: Barbarian + Wizard + Elf + Dwarf.

## Quest IDs
- `pico`: `base:lost_apprentice:pico`
- `lite`: `base:lost_apprentice:lite`
- `medium`: `base:lost_apprentice:medium`
- `heavy`: `base:lost_apprentice:heavy`

## Success behaviors
- heroes announce which room they will check
- negative information is shared to prune the search
- party regroups around the found target before extracting

## Common failure modes
- multiple heroes search the same room silently
- found target is moved without escort
- search continues after rescue mode should begin

## Review signals in traces/replays
- unique rooms searched
- duplicate searches
- messages with search results
- distance to rescuer after target found

## Coordination skills
- divide search lanes and report negative findings
- keep a rescuer within support distance
- switch from search to escort once the target is found

## Pressure sources
- uncertain target location
- minor wandering threats
- hazards near rescue target
- return escort
