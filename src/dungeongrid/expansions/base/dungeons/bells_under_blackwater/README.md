# Bells Under Blackwater

## MARL purpose
Tests whether individual local actions account for a global shared cost such as ringing bells, alert, or flood pressure.

## Tier coverage
- `pico`: A one-hero micro-probe that exposes the first shared global externality decision without side branches.
- `lite`: A two-hero diagnostic focused on communication and first coordination failure modes for shared global externality.
- `medium`: The legacy full task geometry, preserved as the canonical medium tier.
- `heavy`: A four-hero stress variant with additional lanes, side pressure, and stricter shared global externality review signals.

## Recommended heroes by tier
- `pico`: 1 hero: Wizard.
- `lite`: 2 heroes: Barbarian + Wizard.
- `medium`: 3 heroes: Barbarian + Wizard + Dwarf.
- `heavy`: 4 heroes: Barbarian + Wizard + Elf + Dwarf.

## Quest IDs
- `pico`: `base:bells_under_blackwater:pico`
- `lite`: `base:bells_under_blackwater:lite`
- `medium`: `base:bells_under_blackwater:medium`
- `heavy`: `base:bells_under_blackwater:heavy`

## Success behaviors
- heroes warn before interacting with noisy or risky objects
- party stops optional actions once global pressure is high
- team changes route when shared danger crosses a threshold

## Common failure modes
- one hero repeatedly raises danger while others pay the cost
- global pressure is treated as someone else's problem
- risk state is never communicated after a trigger

## Review signals in traces/replays
- global alert increments
- warnings before risky actions
- risk-causing hero distribution
- route changes after externality

## Coordination skills
- announce actions that raise shared danger
- budget global alert/flood risk across the team
- choose collective safety over local action value

## Pressure sources
- shared alert budget
- bell/flood triggers
- remote consequences
- optional loot
