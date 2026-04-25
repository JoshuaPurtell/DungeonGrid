# The Lost Apprentice

## MARL design identity

**Primary MARL axis:** fragile escort with communication-dependent calming.

**Coordination type:** find-calm-guide extraction.

**Theme:** A frightened apprentice hides in a record room and will panic unless the party finds the right phrase.

**Core problem:** Agents must decide whether to invest in information that makes escort safer, then maintain a protective route.

## Challenges posed to agents

- Find the calming clue
- Reach apprentice before alarm grows
- Guide instead of over-clearing
- Keep escort and support within range

## Dilemmas and difficulties

- Calming phrase costs time but lowers escort risk
- Fast rescue may panic the apprentice
- The elf can scout ahead but must report back

## Specific multi-agent coordination problems

- Escort triangle
- Information-to-action transfer
- Route pre-clearing
- Abandoning optional loot

## Warden ReAct runbook notes

Warden should use the dungeon's authored mechanics to test the MARL axis, not generic attrition.

- Pressure the route, not the captive with cheap damage
- Use panic if heroes ignore clues
- Reward calm-and-preclear planning
- Attack isolated rear guards

## Lite variant

**Quest id:** `lost_apprentice_lite`

**File:** `../lost_apprentice_lite/quest.json`

**Designed party:** 2 heroes: elf, wizard.

**Scale:** 4 rooms, one core objective, one optional temptation, and short extraction.

A small rescue: one clue object, one apprentice objective, and a short route where guide/support spacing matters.

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
