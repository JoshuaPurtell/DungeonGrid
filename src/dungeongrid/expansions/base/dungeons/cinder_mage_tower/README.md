# Cinder Mage Tower

## MARL purpose
Tests whether agents identify and neutralize ranged casters before spending turns on nearer but lower-priority targets.

## Tier coverage
- `pico`: A one-hero micro-probe that exposes the first target priority under ranged threat decision without side branches.
- `lite`: A two-hero diagnostic focused on communication and first coordination failure modes for target priority under ranged threat.
- `medium`: The legacy full task geometry, preserved as the canonical medium tier.
- `heavy`: A four-hero stress variant with additional lanes, side pressure, and stricter target priority under ranged threat review signals.

## Recommended heroes by tier
- `pico`: 1 hero: Wizard.
- `lite`: 2 heroes: Barbarian + Wizard.
- `medium`: 3 heroes: Barbarian + Wizard + Dwarf.
- `heavy`: 4 heroes: Barbarian + Wizard + Elf + Dwarf.

## Quest IDs
- `pico`: `base:cinder_mage_tower:pico`
- `lite`: `base:cinder_mage_tower:lite`
- `medium`: `base:cinder_mage_tower:medium`
- `heavy`: `base:cinder_mage_tower:heavy`

## Success behaviors
- party marks casters as priority immediately
- frontline opens space while ranged heroes attack casters
- heroes avoid chasing blockers while mages keep firing

## Common failure modes
- nearest weak monster is attacked while caster remains active
- heroes stand in long sight lanes without cover
- no one communicates the target priority switch

## Review signals in traces/replays
- turns caster remains alive after reveal
- focus-fire consistency
- damage taken from range
- cover/door use

## Coordination skills
- call out ranged line-of-sight threats
- focus fire high-priority casters
- use cover, doors, and interrupts before advancing

## Pressure sources
- ranged cinder mages
- line-of-sight corridors
- screens of weak guards
- torch/alert tempo
