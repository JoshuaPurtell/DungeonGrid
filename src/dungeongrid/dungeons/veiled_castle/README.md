# Veiled Castle

## MARL design identity

**Primary MARL axis:** compositional partial-observation final.

**Coordination type:** belief, clue, counterplay, and extraction composition.

**Theme:** A veiled mini-castle where the right door, the true guard, and the safe exit are all only partly observable.

**Core problem:** This lite finale composes map communication, decoy verification, ranged threat management, and objective extraction.

## Challenges posed to agents

- Share door/clue observations
- Verify the mirror guard
- Avoid exposing the wizard to the mage
- Extract with the token after choosing the true route

## Dilemmas and difficulties

- More clues reduce risk but spend torch
- The secret-like lower route is safer only if verified
- Countering the mage may leave the objective unguarded

## Specific multi-agent coordination problems

- Hierarchical planning
- Shared belief
- Multi-threat priority
- Compositional transfer

## Warden ReAct runbook notes

Warden should use the dungeon's authored mechanics to test the MARL axis, not generic attrition.

- Use decoys and ranged pressure within legal vision
- Reward verified route choice
- Punish isolated objective carriers
- Do not combine all pressures at once before the heroes reveal them

## Lite variant

**Quest id:** `veiled_castle_lite`

**File:** `../veiled_castle_lite/quest.json`

**Designed party:** 2 heroes: elf, wizard.

**Scale:** 4 rooms, one core objective, one optional temptation, and short extraction.

A four-room mini-finale with one decoy, one ranged threat, one objective, and enough doors to require explicit communication.

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
