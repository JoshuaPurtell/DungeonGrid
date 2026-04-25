# Trial of Embers

## MARL design identity

**Primary MARL axis:** multi-objective sequencing with non-dominant strategies.

**Coordination type:** proof selection and resource preservation.

**Theme:** Three ember bowls ask for proof of courage, care, and restraint before the door cools.

**Core problem:** The agents must choose an ordering across combat, hazard, and restraint objectives; the best order depends on party state.

## Challenges posed to agents

- Identify three proof objects
- Sequence subtasks
- Preserve spells/tools
- Avoid treating every proof as combat

## Dilemmas and difficulties

- Courage path is direct but damaging
- Care path consumes dwarf actions
- Restraint path sacrifices treasure but lowers pressure

## Specific multi-agent coordination problems

- Task decomposition
- Sequencing
- Resource conservation
- Strategy selection

## Warden ReAct runbook notes

Warden should use the dungeon's authored mechanics to test the MARL axis, not generic attrition.

- Adapt pressure to chosen proof order
- Do not make combat always optimal
- Reward restraint when chosen coherently
- Punish scattered subtask switching

## Lite variant

**Quest id:** `trial_of_embers_lite`

**File:** `../trial_of_embers_lite/quest.json`

**Designed party:** 2 heroes: wizard, dwarf.

**Scale:** 4 rooms, one core objective, one optional temptation, and short extraction.

A four-room proof sampler: one hazard, one combat threat, one optional restraint object, and a final ember token.

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
