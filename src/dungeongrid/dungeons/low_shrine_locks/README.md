# Low Shrine Locks

## MARL design identity

**Primary MARL axis:** joint-action synchronization.

**Coordination type:** ready-check and simultaneous activation.

**Theme:** A sunken shrine whose two knee-high plinths must be held while the center lock is opened.

**Core problem:** The goal requires synchronized decentralized action; waiting and messaging become productive actions.

## Challenges posed to agents

- Discover linked locks
- Use messages for ready checks
- Hold exposed plinths
- Collapse back together after opening

## Dilemmas and difficulties

- Splitting solves quickly but exposes both heroes
- Premature activation wastes turns
- The dwarf can hold a plinth or disarm the trap, not both

## Specific multi-agent coordination problems

- Joint action dependency
- Temporal synchronization
- Ready protocol
- Split-and-regroup discipline

## Warden ReAct runbook notes

Warden should use the dungeon's authored mechanics to test the MARL axis, not generic attrition.

- Disrupt timing rather than simply dealing damage
- Harass exposed holders
- Let clean synchronization succeed
- Punish premature solo activation

## Lite variant

**Quest id:** `low_shrine_locks_lite`

**File:** `../low_shrine_locks_lite/quest.json`

**Designed party:** 2 heroes: dwarf, elf.

**Scale:** 4 rooms, one core objective, one optional temptation, and short extraction.

A duo-first two-plinth shrine: two side rooms, center objective, and explicit ready-check pressure.

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
