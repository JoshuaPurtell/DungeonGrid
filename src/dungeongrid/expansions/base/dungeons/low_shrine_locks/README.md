# Low Shrine Locks

## MARL purpose
Tests whether independently acting heroes can synchronize door, lock, and objective timing instead of greedily advancing alone.

## Tier coverage
- `pico`: A one-hero micro-probe that exposes the first joint-action synchronization decision without side branches.
- `lite`: A two-hero diagnostic focused on communication and first coordination failure modes for joint-action synchronization.
- `medium`: The legacy full task geometry, preserved as the canonical medium tier.
- `heavy`: A four-hero stress variant with additional lanes, side pressure, and stricter joint-action synchronization review signals.

## Recommended heroes by tier
- `pico`: 1 hero: Wizard.
- `lite`: 2 heroes: Barbarian + Wizard.
- `medium`: 3 heroes: Barbarian + Wizard + Dwarf.
- `heavy`: 4 heroes: Barbarian + Wizard + Elf + Dwarf.

## Quest IDs
- `pico`: `base:low_shrine_locks:pico`
- `lite`: `base:low_shrine_locks:lite`
- `medium`: `base:low_shrine_locks:medium`
- `heavy`: `base:low_shrine_locks:heavy`

## Success behaviors
- heroes declare which lock or door they cover
- one hero waits or guards instead of breaking synchronization
- objective pickup happens after both return routes are understood

## Common failure modes
- single hero opens a pressure room before the partner is ready
- both heroes chase the same lock while the other gate remains closed
- silent AP spending causes a stalled or unsafe route

## Review signals in traces/replays
- same-round lock progress
- messages before opens
- doorway waits
- split-party delay

## Coordination skills
- announce lock/door intent before spending AP
- hold positions until paired progress is possible
- sequence search, open, and carry actions across separated lanes

## Pressure sources
- paired locks
- separated lanes
- door timing
- minor sentries
