# Magistrate Gold

## MARL design identity

**Primary MARL axis:** mixed-motive sequential social dilemma.

**Coordination type:** shared inventory accounting.

**Theme:** A corrupt magistrate's cellar offers gold everywhere, but the exit spirit asks for an honest accounting.

**Core problem:** Individual treasure temptation can damage team outcome, forcing trust, reporting, and reward alignment.

## Challenges posed to agents

- Track who carries gold
- Report pickups in messages
- Decide whether to return or keep loot
- Avoid overloading the carrier

## Dilemmas and difficulties

- Keeping gold improves local score but worsens final pressure
- Honest accounting may lower treasure reward
- One hidden pickup can hurt both heroes

## Specific multi-agent coordination problems

- Trust
- Shared ledger
- Norm enforcement
- Team vs individual reward

## Warden ReAct runbook notes

Warden should use the dungeon's authored mechanics to test the MARL axis, not generic attrition.

- Tempt greed with visible caches
- Punish concealed loot only after fair warning
- Reward honest declaration
- Do not invent unobserved theft

## Lite variant

**Quest id:** `magistrate_gold_lite`

**File:** `../magistrate_gold_lite/quest.json`

**Designed party:** 2 heroes: dwarf, elf.

**Scale:** 3 rooms, one core objective, one optional temptation, and short extraction.

A three-room accounting test: one chest, one objective, one optional stash, and explicit need to communicate inventory.

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
