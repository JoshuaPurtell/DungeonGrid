# Glass Maze

## MARL purpose
Tests whether partial observations are turned into shared route memory through messages and disciplined exploration.

## Tier coverage
- `pico`: A one-hero micro-probe that exposes the first shared map memory decision without side branches.
- `lite`: A two-hero diagnostic focused on communication and first coordination failure modes for shared map memory.
- `medium`: The legacy full task geometry, preserved as the canonical medium tier.
- `heavy`: A four-hero stress variant with additional lanes, side pressure, and stricter shared map memory review signals.

## Recommended heroes by tier
- `pico`: 1 hero: Wizard.
- `lite`: 2 heroes: Barbarian + Wizard.
- `medium`: 3 heroes: Barbarian + Wizard + Dwarf.
- `heavy`: 4 heroes: Barbarian + Wizard + Elf + Dwarf.

## Quest IDs
- `pico`: `base:glass_maze:pico`
- `lite`: `base:glass_maze:lite`
- `medium`: `base:glass_maze:medium`
- `heavy`: `base:glass_maze:heavy`

## Success behaviors
- scouts report branch outcomes succinctly
- party maintains a common route plan to the objective and exit
- heroes mark hazards before teammates arrive

## Common failure modes
- agents rediscover the same corridors independently
- secret doors are found but not communicated
- carrier gets lost after pickup

## Review signals in traces/replays
- route-message count
- repeated dead-end visits
- secret searches after hints
- tiles revealed per action

## Coordination skills
- name landmarks and dead ends in messages
- avoid duplicate scouting of already-known branches
- share secret-door and trap information before movement

## Pressure sources
- maze branches
- mirror decoys
- secret doors
- limited line of sight
