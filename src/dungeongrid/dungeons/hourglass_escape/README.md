# Hourglass Escape

## MARL design identity

**Primary MARL axis:** decentralized scheduling under deadline.

**Coordination type:** timed route and objective sequencing.

**Theme:** A narrow hourglass chamber where sand blocks the slow route after the objective is touched.

**Core problem:** The team must schedule exploration, pickup, and extraction before the graph effectively changes.

## Challenges posed to agents

- Estimate deadline
- Clear or ignore side route
- Choose pickup timing
- Keep slow hero from being cut off

## Dilemmas and difficulties

- Pre-clearing costs time but prevents disaster
- The elf can scout fast but may trigger too early
- The sentinel is slow but dangerous in a timed choke

## Specific multi-agent coordination problems

- Timed sequencing
- Deadline-aware routing
- Split-regroup timing
- Action budget planning

## Warden ReAct runbook notes

Warden should use the dungeon's authored mechanics to test the MARL axis, not generic attrition.

- Use the clock as the main pressure
- Block the greedy side route, not the only escape
- Reward planned extraction
- Make deadline warnings explicit

## Lite variant

**Quest id:** `hourglass_escape_lite`

**File:** `../hourglass_escape_lite/quest.json`

**Designed party:** 2 heroes: elf, barbarian.

**Scale:** 4 rooms, one core objective, one optional temptation, and short extraction.

A four-room escape clock with a sentinel and a bottom route; the agents must decide when to pick up the sand key.

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
