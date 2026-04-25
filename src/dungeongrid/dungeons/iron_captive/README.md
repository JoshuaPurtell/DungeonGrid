# Iron Captive

## MARL design identity

**Primary MARL axis:** escort and protection of constrained third-party state.

**Coordination type:** front-guard rear-guard rescue formation.

**Theme:** An iron chair holds a captive whose chains squeal whenever the party rushes the rescue.

**Core problem:** The objective behaves like a fragile dependency: rescue is not enough; extraction with formation matters.

## Challenges posed to agents

- Reach captive safely
- Disarm or unlock chains
- Choose who escorts
- Avoid exposing the captive route

## Dilemmas and difficulties

- Breaking chains is fast but noisy
- Picking the lock is safer but exposes the dwarf
- The barbarian can guard or carry, not both

## Specific multi-agent coordination problems

- Protect-the-specialist
- Escort formation
- Unlock timing
- Rear-guard withdrawal

## Warden ReAct runbook notes

Warden should use the dungeon's authored mechanics to test the MARL axis, not generic attrition.

- Pressure the route and the unlocker
- Do not cheaply kill the captive
- Reward pre-clearing
- Use the sentinel to force formation decisions

## Lite variant

**Quest id:** `iron_captive_lite`

**File:** `../iron_captive_lite/quest.json`

**Designed party:** 2 heroes: barbarian, dwarf.

**Scale:** 4 rooms, one core objective, one optional temptation, and short extraction.

A four-room rescue with one captive marker, one lock/trap, and a sentinel guarding the return route.

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
