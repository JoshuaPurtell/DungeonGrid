# The Lantern Crypt

## MARL design identity

**Primary MARL axis:** role-specialized causal counterplay.

**Coordination type:** support action before damage commitment.

**Theme:** A crypt guardian draws strength from a lantern-altar that only the careful reader understands.

**Core problem:** The optimal team policy asks one hero to spend turns on clue/counterplay while the other prevents the boss from collapsing the party.

## Challenges posed to agents

- Infer altar-guardian link
- Assign clue-reader or altar-breaker
- Delay boss commitment until counterplay
- Protect the support hero

## Dilemmas and difficulties

- Destroying the altar weakens the boss but raises alert
- Reading the altar is safer but slower
- The barbarian wants to fight before the wizard is done

## Specific multi-agent coordination problems

- Support-role credit
- Timing the engage
- Frontline screening
- Causal information sharing

## Warden ReAct runbook notes

Warden should use the dungeon's authored mechanics to test the MARL axis, not generic attrition.

- Protect the altar after heroes identify it
- Punish direct boss rushing
- Let counterplay visibly matter
- Do not hide the causal clue unfairly

## Lite variant

**Quest id:** `lantern_crypt_lite`

**File:** `../lantern_crypt_lite/quest.json`

**Designed party:** 2 heroes: wizard, barbarian.

**Scale:** 3 rooms, one core objective, one optional temptation, and short extraction.

A boss-counterplay capsule: entry, altar clue, objective, and one guardian whose difficulty hinges on support action.

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
