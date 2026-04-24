# DungeonGrid

DungeonGrid is a text-first cooperative dungeon-crawl environment for
multi-agent benchmarks.

It is designed around:

- one to four submitted hero agents;
- an always-AI Warden / dungeon-controller side;
- compact text board-state observations;
- structured JSON action plans instead of string actions;
- batched OpenEnv ReAct-style plan execution with reveal-boundary replanning;
- fixed quest difficulty across solo, duo, trio, and squad slices.

This package is currently an alpha extraction of the DungeonGrid engine that is
being integrated into NanoCoop.

## Quick Start

```python
from dungeongrid import DungeonGridEnvironment

env = DungeonGridEnvironment()
obs = env.reset(quest_id="lantern_crypt", num_heroes=2, seed=1)
print(obs.text)

result = env.act_plan(
    intent="Scout east, then report back to the party.",
    actions=[
        {"type": "move", "direction": "east"},
        {"type": "message", "target": "party", "payload": {"text": "I am checking the east passage."}},
    ],
)
print(result.skipped_actions)
print(result.observation.text)
```

## OpenEnv ReAct Contract

Agents receive compact text observations and submit one structured tool call per
decision point:

```json
{
  "name": "dungeongrid_act",
  "arguments": {
    "intent": "Open the east door and stop if a room is revealed.",
    "actions": [
      {"type": "open_door", "target": "door_1"},
      {"type": "move", "direction": "east"}
    ]
  }
}
```

Agents can query compact rule details with `dungeongrid_rules({"topic":
"actions"})`. Public observations do not expose legal action lists; the
environment validates proposed JSON actions, skips illegal queued actions, and
renders concrete feedback in later observations.

Reveal boundaries stop queued execution so the agent can replan after new board
state appears, such as opened doors, revealed traps, opened chests, objective
changes, turn end, or episode end.

```python
from dungeongrid import dungeongrid_rules

print(dungeongrid_rules("movement"))
```

## Quests

Bundled alpha quests:

- `lantern_crypt`
- `bells_under_blackwater`
- `ashen_pantry`
- `cinder_exit`
- `low_shrine_locks`

## Status

DungeonGrid is under active development. Public names use DungeonGrid, while
some compatibility aliases for the earlier TorchGrid prototype remain in the
Python API to ease migration.
