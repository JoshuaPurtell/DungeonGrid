# Black Standard Keep

## MARL design identity

**Primary MARL axis:** opponent-aware breach sequencing.

**Coordination type:** threshold control against a tactical defender.

**Theme:** A miniature guard keep built around a black war-standard that lets defenders rally if doors are opened carelessly.

**Core problem:** The heroes must coordinate door timing and target priority against Warden as a tactical ReAct defender.

## Challenges posed to agents

- Open one front at a time
- Use the barbarian as threshold anchor
- Use the elf to punish retreating defenders
- Prevent the sentinel from holding the objective door

## Dilemmas and difficulties

- Waiting gives defenders time to form a line
- Rushing creates crossfire
- The standard can be searched for reward or destroyed for tempo

## Specific multi-agent coordination problems

- Breach order
- Frontline/backline spacing
- Shared target focus
- Adversarial tempo control

## Warden ReAct runbook notes

Warden should use the dungeon's authored mechanics to test the MARL axis, not generic attrition.

- Hold thresholds
- Retreat wounded guards behind the sentinel
- Punish multiple open fronts
- Do not suicide defenders into obvious kill zones

## Lite variant

**Quest id:** `black_standard_keep_lite`

**File:** `../black_standard_keep_lite/quest.json`

**Designed party:** 2 heroes: barbarian, elf.

**Scale:** 4 rooms, one core objective, one optional temptation, and short extraction.

Four-room keep: two doors, one rally object, one sentinel, and a clear test of whether agents avoid opening both fronts.

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
