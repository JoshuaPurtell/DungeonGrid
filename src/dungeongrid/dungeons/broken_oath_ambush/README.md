# Broken Oath Ambush

## MARL design identity

**Primary MARL axis:** contingency planning under hidden threat.

**Coordination type:** bait-cover-fallback protocol.

**Theme:** An oath hall where a false safe route is really a killing lane.

**Core problem:** Agents must create a fallback plan before triggering the obvious route, then communicate when the ambush has started.

## Challenges posed to agents

- Read warning clues
- Keep the dwarf close enough to detect the trap
- Hold a reserve action for the ambush
- Avoid chasing the first visible enemy alone

## Dilemmas and difficulties

- The direct route is fastest but exposed
- Pre-searching costs tempo
- The frontline can bait safely only if support is positioned

## Specific multi-agent coordination problems

- Ambush protocol
- Reserve positioning
- Trap specialist timing
- Fallback route agreement

## Warden ReAct runbook notes

Warden should use the dungeon's authored mechanics to test the MARL axis, not generic attrition.

- Spring pressure after overextension
- Do not punish teams that actually scout
- Try to split bait from support
- Keep ambush consequences readable

## Lite variant

**Quest id:** `broken_oath_ambush_lite`

**File:** `../broken_oath_ambush_lite/quest.json`

**Designed party:** 2 heroes: barbarian, dwarf.

**Scale:** 3 rooms, one core objective, one optional temptation, and short extraction.

A short oath hall with one trap and one guard: the whole test is whether the pair scouts before stepping into the lane.

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
