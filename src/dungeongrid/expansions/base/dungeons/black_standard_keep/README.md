# Black Standard Keep

## MARL purpose
Tests distributed lane ownership and rally-point discipline in a keep with multiple defensive pockets.

## Tier coverage
- `pico`: A one-hero micro-probe that exposes the first lane assignment under fortress pressure decision without side branches.
- `lite`: A two-hero diagnostic focused on communication and first coordination failure modes for lane assignment under fortress pressure.
- `medium`: The legacy full task geometry, preserved as the canonical medium tier.
- `heavy`: A four-hero stress variant with additional lanes, side pressure, and stricter lane assignment under fortress pressure review signals.

## Recommended heroes by tier
- `pico`: 1 hero: Wizard.
- `lite`: 2 heroes: Barbarian + Wizard.
- `medium`: 3 heroes: Barbarian + Wizard + Dwarf.
- `heavy`: 4 heroes: Barbarian + Wizard + Elf + Dwarf.

## Quest IDs
- `pico`: `base:black_standard_keep:pico`
- `lite`: `base:black_standard_keep:lite`
- `medium`: `base:black_standard_keep:medium`
- `heavy`: `base:black_standard_keep:heavy`

## Success behaviors
- heroes declare which lane they are holding
- scouts report before the team commits to a breach
- party regroups before objective extraction

## Common failure modes
- two heroes abandon the same flank
- newly revealed guards are ignored while looting
- isolated hero triggers a room without support

## Review signals in traces/replays
- lane coverage
- messages after new room reveal
- turns isolated
- alarm/alert growth

## Coordination skills
- assign lanes before opening fortress doors
- collapse to a rally point when pressure spikes
- share status updates across separated rooms

## Pressure sources
- fortress doors
- multi-lane guards
- alarm cultists
- optional cache detours
