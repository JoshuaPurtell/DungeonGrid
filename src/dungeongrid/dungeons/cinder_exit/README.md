# Cinder Exit

## MARL design identity

**Primary MARL axis:** cooperative extraction under pursuit.

**Coordination type:** carrier escort and rear-guard handoff.

**Theme:** A burning back passage where the objective gets heavier as the route fills with cinders.

**Core problem:** The team must pre-plan extraction, decide who carries the object, and decide when the rear guard stops delaying and runs.

## Challenges posed to agents

- Choose carrier
- Pre-clear a return route
- Avoid letting the carrier become isolated
- Use the fast hero to scout but not abandon the frontline

## Dilemmas and difficulties

- The barbarian carries safely but is needed to hold pursuers
- The elf extracts quickly but is fragile
- Fighting every pursuer loses the clock

## Specific multi-agent coordination problems

- Carrier protection
- Rear-guard timing
- Dynamic role reassignment
- Extraction route reservation

## Warden ReAct runbook notes

Warden should use the dungeon's authored mechanics to test the MARL axis, not generic attrition.

- Pressure the carrier after pickup
- Use pursuers to force handoff decisions
- Reward pre-cleared routes
- Do not body-block the exit without warning

## Lite variant

**Quest id:** `cinder_exit_lite`

**File:** `../cinder_exit_lite/quest.json`

**Designed party:** 2 heroes: elf, barbarian.

**Scale:** 4 rooms, one core objective, one optional temptation, and short extraction.

Four-room extraction race with a mauler near the objective and a lower return route that can be pre-cleared.

The lite version is intended for smaller LLMs and faster MARL rollouts. It isolates the essential dynamic while preserving the same observation/action grammar: door reveal, communication, role assignment, objective pickup, and extraction.

## Evaluation notes

Useful metrics for this dungeon:

- coordination messages before irreversible actions;
- duplicate or wasted searches;
- whether the coordination-critical support action happened;
- objective-carrier isolation turns;
- Warden pressure source attribution;
- success with both heroes alive in the lite variant.

## Originality / safety note

This README describes an original MARL challenge contract for DungeonGrid. It intentionally avoids reproducing protected quest names, map geometry, prose, room contents, or placement patterns from any commercial dungeon-crawl product.
