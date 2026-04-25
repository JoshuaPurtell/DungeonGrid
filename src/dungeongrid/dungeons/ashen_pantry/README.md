# The Ashen Pantry

## MARL design identity

**Primary MARL axis:** decentralized task allocation under costly search.

**Coordination type:** divide-and-report exploration.

**Theme:** A burned monastery pantry where every shelf is either a ration, a clue, or unnecessary noise.

**Core problem:** Agents must split low-risk search tasks, avoid duplicate interactions, and leave once the ledger is recovered instead of turning a tutorial into a greed spiral.

## Challenges posed to agents

- Assign distinct search targets
- Use trap/secret searches before touching suspicious shelves
- Stop searching after the objective is secured
- Use the secret hatch only if its search cost is justified

## Dilemmas and difficulties

- Extra pantry loot increases score but consumes turns and may raise alert
- The hazard specialist is useful searching, but also needs protection
- Solo play favors a compact route; duo play rewards division of labor

## Specific multi-agent coordination problems

- Redundant-action avoidance
- Shared map update after the secret hatch
- Specialist protection while searching
- Exit timing after objective pickup

## Warden ReAct runbook notes

Warden should use the dungeon's authored mechanics to test the MARL axis, not generic attrition.

- Apply only mild vermin pressure
- Punish repeated redundant searching, not initial caution
- Let an early clean extraction succeed
- Use the secret cache as temptation rather than mandatory content

## Lite variant

**Quest id:** `ashen_pantry_lite`

**File:** `../ashen_pantry_lite/quest.json`

**Designed party:** 2 heroes: elf, dwarf.

**Scale:** 3 rooms, one core objective, one optional temptation, and short extraction.

Three-room search discipline: one suspicious shelf, one hidden hatch, one objective room, and a short extraction.

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
