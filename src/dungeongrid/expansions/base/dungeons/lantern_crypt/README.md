# Lantern Crypt

## MARL purpose
Tests whether heroes value clue reading and altar counterplay before committing damage into a strengthened guardian.

## Tier coverage
- `pico`: A one-hero micro-probe that exposes the first role-specialized causal counterplay decision without side branches.
- `lite`: A two-hero diagnostic focused on communication and first coordination failure modes for role-specialized causal counterplay.
- `medium`: The legacy full task geometry, preserved as the canonical medium tier.
- `heavy`: A four-hero stress variant with additional lanes, side pressure, and stricter role-specialized causal counterplay review signals.

## Recommended heroes by tier
- `pico`: 1 hero: Wizard.
- `lite`: 2 heroes: Barbarian + Wizard.
- `medium`: 3 heroes: Barbarian + Wizard + Dwarf.
- `heavy`: 4 heroes: Barbarian + Wizard + Elf + Dwarf.

## Quest IDs
- `pico`: `base:lantern_crypt:pico`
- `lite`: `base:lantern_crypt:lite`
- `medium`: `base:lantern_crypt:medium`
- `heavy`: `base:lantern_crypt:heavy`

## Success behaviors
- one hero investigates or breaks the altar before the party rushes the boss
- frontline pressure keeps the support hero safe during setup
- the party commits damage after sharing the causal clue

## Common failure modes
- heroes attack the guardian before reading the lantern clue
- the support hero is left exposed while doing the coordination-critical work
- the party never communicates that counterplay has changed the fight

## Review signals in traces/replays
- counterplay before boss damage
- messages about altar rules
- frontline screens
- support isolation turns

## Coordination skills
- assign a clue reader or altar breaker before the boss engage
- screen the support hero while counterplay is prepared
- communicate when the guardian has been weakened enough to commit

## Heavy role challenges
- `wizard`: read or break the ember altar so the guardian is not treated as a normal damage race.
- `barbarian`: screen the altar reader, then commit pressure after counterplay is active.
- `elf`: scout the lens cache and confirm the altar tether before the idol run.
- `dwarf`: mark the secret return route and manage hazard/route risk.

## Heavy tandem checks
- Wizard + Barbarian: counterplay reader protected by frontline screening.
- Elf + Dwarf: scout-confirmed tether route converted into a marked extraction path.

## Pressure sources
- lantern altar
- boss guardian
- support tempo cost
- alert from counterplay
