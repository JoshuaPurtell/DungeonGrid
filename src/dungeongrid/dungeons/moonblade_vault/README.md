# Moonblade Vault

## MARL design identity

**Primary MARL axis:** heterogeneous role-task assignment.

**Coordination type:** scout-disarm-handoff.

**Theme:** A silver vault only opens when moonlight is reflected through a blade-shaped slit.

**Core problem:** Different subtasks favor different heroes: scouting reflection lines, disarming vault wards, and carrying the blade token.

## Challenges posed to agents

- Match hero to subtask
- Avoid wrong-role inefficiency
- Hand off the vault token if needed
- Use the lower route to bypass the sentinel

## Dilemmas and difficulties

- The elf sees routes quickly but cannot safely handle the trap
- The dwarf can open the vault but is slower
- Carrying the blade may expose the scout

## Specific multi-agent coordination problems

- Role-task matching
- Handoff
- Parallel subtask sequencing
- Heterogeneous-agent planning

## Warden ReAct runbook notes

Warden should use the dungeon's authored mechanics to test the MARL axis, not generic attrition.

- Pressure wrong-role assignments
- Guard the handoff point
- Respect successful disarm/scout play
- Avoid making one role mandatory for basic success

## Lite variant

**Quest id:** `moonblade_vault_lite`

**File:** `../moonblade_vault_lite/quest.json`

**Designed party:** 2 heroes: elf, dwarf.

**Scale:** 4 rooms, one core objective, one optional temptation, and short extraction.

A compact vault where one hero scouts reflection, the other handles hazard, and the token may need a handoff.

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
