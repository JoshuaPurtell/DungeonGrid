# Tusk Warlord Lair

## MARL design identity

**Primary MARL axis:** formation control against cleave pressure.

**Coordination type:** frontline pin with ranged spacing.

**Theme:** A cramped lair where a tusked warlord punishes clustered heroes and sloppy doorway entries.

**Core problem:** Agents must coordinate spacing: the frontline pins while the ranged hero avoids adjacency and preserves line of sight.

## Challenges posed to agents

- Avoid clustering
- Use doorway and side room deliberately
- Coordinate ranged pressure with melee pin
- Do not let the warlord reach the backline

## Dilemmas and difficulties

- Close formation protects against small enemies but invites cleave
- Wide formation preserves safety but complicates support
- Optional chest draws attention away from spacing

## Specific multi-agent coordination problems

- Formation control
- Threat zoning
- Frontline/backline roles
- Target focus

## Warden ReAct runbook notes

Warden should use the dungeon's authored mechanics to test the MARL axis, not generic attrition.

- Punish adjacent clustering
- Try to break the pin if the elf overextends
- Do not chase through bad terrain forever
- Reward clean spacing

## Lite variant

**Quest id:** `tusk_warlord_lair_lite`

**File:** `../tusk_warlord_lair_lite/quest.json`

**Designed party:** 2 heroes: barbarian, elf.

**Scale:** 3 rooms, one core objective, one optional temptation, and short extraction.

One boss-room lair with a lower lure/chest route; the essential test is spacing under cleave threat.

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
