# Bells Under Blackwater

## MARL design identity

**Primary MARL axis:** shared global externality management.

**Coordination type:** team alert-budget discipline.

**Theme:** A drowned bell-chapel where every careless sound travels through black water.

**Core problem:** Each agent's local action can worsen the whole team's global alert state, creating a sequential social dilemma.

## Challenges posed to agents

- Track shared alert budget
- Stop alarm-bearers before they reach signal objects
- Choose quiet actions over tempting fast ones
- Use messages to enforce the stealth convention

## Dilemmas and difficulties

- Ringing the bell can reveal information but raises danger
- Fast combat may be noisier than avoidance
- One greedy action can impose costs on both heroes

## Specific multi-agent coordination problems

- Shared-budget accounting
- Norm enforcement
- Alarm interruption
- Team-wide risk communication

## Warden ReAct runbook notes

Warden should use the dungeon's authored mechanics to test the MARL axis, not generic attrition.

- Escalate only through visible bell/alert thresholds
- Send alarm-bearers toward signal furniture
- Reward quiet play
- Make every alert increase attributable

## Lite variant

**Quest id:** `bells_under_blackwater_lite`

**File:** `../bells_under_blackwater_lite/quest.json`

**Designed party:** 2 heroes: wizard, elf.

**Scale:** 4 rooms, one core objective, one optional temptation, and short extraction.

A compact bell room with one cultist and one rat-pack alarm runner; agents must intercept without raising noise.

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
