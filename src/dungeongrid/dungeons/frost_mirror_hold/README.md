# Frost Mirror Hold

## MARL design identity

**Primary MARL axis:** belief-state fusion under decoys.

**Coordination type:** shared observation and verification.

**Theme:** A frozen mirror-room where reflections make one threat look like two and two doors look like one.

**Core problem:** Each hero gets ambiguous evidence; they must compare observations before committing attacks or routes.

## Challenges posed to agents

- Report observed mirror clues
- Verify the real adept before spending spells
- Avoid duplicate exploration
- Keep a shared belief of which room is real

## Dilemmas and difficulties

- Verification costs time
- Premature attacks waste resources
- Splitting improves observations but risks isolation

## Specific multi-agent coordination problems

- Belief merging
- Communication compression
- Observation verification
- Partial-observation conflict resolution

## Warden ReAct runbook notes

Warden should use the dungeon's authored mechanics to test the MARL axis, not generic attrition.

- Exploit inconsistent beliefs through decoy movement
- Respect verified mirror states
- Do not use omniscient counters
- Make false positives costly but not lethal

## Lite variant

**Quest id:** `frost_mirror_hold_lite`

**File:** `../frost_mirror_hold_lite/quest.json`

**Designed party:** 2 heroes: elf, wizard.

**Scale:** 4 rooms, one core objective, one optional temptation, and short extraction.

Four-room mirror hold with one mirror adept and one ordinary guard; the lesson is to verify before committing.

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
