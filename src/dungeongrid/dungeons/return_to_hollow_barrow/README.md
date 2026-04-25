# Return to Hollow Barrow

## MARL design identity

**Primary MARL axis:** transfer and adaptation to a changed environment.

**Coordination type:** reuse old policy while noticing changed dynamics.

**Theme:** The barrow looks familiar, but old safe habits now wake the hollow dead.

**Core problem:** Agents must transfer prior barrow knowledge without overfitting; the return version reverses one key assumption.

## Challenges posed to agents

- Recognize changed cues
- Do not blindly replay the first solution
- Coordinate warding and frontline timing
- Extract before both hollows converge

## Dilemmas and difficulties

- Known shortcut may now be trapped
- Warding one hollow exposes the other
- Direct fighting is reliable but slow

## Specific multi-agent coordination problems

- Transfer robustness
- Belief revision
- Role reassignment
- Two-threat prioritization

## Warden ReAct runbook notes

Warden should use the dungeon's authored mechanics to test the MARL axis, not generic attrition.

- Exploit stale policies through visible changed cues
- Do not hide the reversal
- Use two hollows to force prioritization
- Reward agents that say what changed

## Lite variant

**Quest id:** `return_to_hollow_barrow_lite`

**File:** `../return_to_hollow_barrow_lite/quest.json`

**Designed party:** 2 heroes: barbarian, wizard.

**Scale:** 4 rooms, one core objective, one optional temptation, and short extraction.

A return-map capsule with two hollow threats and one altered route, designed to test transfer rather than raw combat.

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
