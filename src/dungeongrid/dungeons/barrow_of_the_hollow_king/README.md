# Barrow of the Hollow King

## MARL design identity

**Primary MARL axis:** credit assignment for delayed maintenance tasks.

**Coordination type:** fight-cleanse-guard rotation.

**Theme:** A root-filled barrow where defeated bones twitch until someone spends time pinning them under white roots.

**Core problem:** The decisive contribution may be warding or cleaning remains rather than dealing damage, making support-role credit assignment explicit.

## Challenges posed to agents

- Recognize revive pressure
- Assign a remains-cleanup role
- Choose which corpse or root anchor matters
- Avoid all agents tunneling on damage

## Dilemmas and difficulties

- Cleanup reduces future pressure but costs immediate tempo
- The wizard can ward or attack, not both
- The dwarf can manage traps or roots while exposed

## Specific multi-agent coordination problems

- Maintenance role valuation
- Long-horizon credit assignment
- Guarding a non-damaging teammate
- Priority ordering under revive threat

## Warden ReAct runbook notes

Warden should use the dungeon's authored mechanics to test the MARL axis, not generic attrition.

- Revive selectively and legibly
- Protect the root anchor if heroes discover it
- Do not make revives infinite without counterplay
- Pressure teams that ignore cleanup

## Lite variant

**Quest id:** `barrow_of_the_hollow_king_lite`

**File:** `../barrow_of_the_hollow_king_lite/quest.json`

**Designed party:** 2 heroes: dwarf, wizard.

**Scale:** 4 rooms, one core objective, one optional temptation, and short extraction.

A two-threat barrow: one hollow knight, one guard, one root marker, and an objective that accelerates revival pressure.

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
