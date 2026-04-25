# Cinder Mage Tower

## MARL design identity

**Primary MARL axis:** target priority with asymmetric threat ranges.

**Coordination type:** covering advance against ranged control.

**Theme:** A low tower chamber where a cinder mage controls lines of fire from behind cracked braziers.

**Core problem:** Agents must coordinate movement through cover and decide whether to rush the mage or clear the guard first.

## Challenges posed to agents

- Track line of sight
- Use guard/cover before entering mage range
- Coordinate a melee pin with ranged magic
- Avoid both heroes standing in the same kill lane

## Dilemmas and difficulties

- Rushing the mage exposes the wizard
- Clearing the guard gives the mage more shots
- Destroying a brazier weakens the mage but raises alert

## Specific multi-agent coordination problems

- Asymmetric-range planning
- Target priority
- Cover usage
- Support timing

## Warden ReAct runbook notes

Warden should use the dungeon's authored mechanics to test the MARL axis, not generic attrition.

- Use the mage to punish exposed lines
- Keep the guard between heroes and mage
- Do not kite indefinitely
- Reward coordinated pin-and-cast plans

## Lite variant

**Quest id:** `cinder_mage_tower_lite`

**File:** `../cinder_mage_tower_lite/quest.json`

**Designed party:** 2 heroes: wizard, barbarian.

**Scale:** 4 rooms, one core objective, one optional temptation, and short extraction.

Two-threat tower: one ranged mage, one guard, and furniture that teaches cover/counterplay without a long map.

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
