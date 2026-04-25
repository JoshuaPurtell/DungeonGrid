# Glass Maze

## MARL design identity

**Primary MARL axis:** shared map memory and route compression.

**Coordination type:** scout-report-map-update loop.

**Theme:** A glass service maze where the best path is a tiny secret panel, not the obvious corridor.

**Core problem:** Agents must maintain a shared map and avoid redundant looping through already-known paths.

## Challenges posed to agents

- Search for the panel
- Mark which route is real
- Avoid both heroes chasing the same reflection
- Use map messages before objective pickup

## Dilemmas and difficulties

- The secret route saves extraction time but costs a search
- Splitting helps map coverage but creates confusion
- The mirror adept tempts overreaction

## Specific multi-agent coordination problems

- Map synchronization
- Route naming
- Scout trust
- Loop avoidance

## Warden ReAct runbook notes

Warden should use the dungeon's authored mechanics to test the MARL axis, not generic attrition.

- Punish repeated loops with light pressure
- Let correct map-sharing matter
- Use decoys to test shared memory
- Do not randomize the true shortcut mid-run

## Lite variant

**Quest id:** `glass_maze_lite`

**File:** `../glass_maze_lite/quest.json`

**Designed party:** 2 heroes: elf, dwarf.

**Scale:** 3 rooms, one core objective, one optional temptation, and short extraction.

A secret-panel mazelet: one objective room, one optional shortcut, one decoy enemy, and a small lower route.

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
