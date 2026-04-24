# DungeonGrid

DungeonGrid is a text-first cooperative dungeon-crawl environment for
multi-agent benchmarks.

It is designed around:

- one to four submitted hero agents;
- an always-AI Warden / dungeon-controller side;
- compact text board-state observations;
- structured JSON action plans instead of string actions;
- batched plan execution with future reveal-boundary replanning;
- fixed quest difficulty across solo, duo, trio, and squad slices.

This package is currently an alpha extraction of the DungeonGrid engine that is
being integrated into NanoCoop.

## Quick Start

```python
from dungeongrid import DungeonGridEnvironment

env = DungeonGridEnvironment()
obs = env.reset(quest_id="lantern_crypt", num_heroes=2, seed=1)
print(obs.text)

step = env.step({"type": "message", "target": "party", "payload": {"text": "I'll scout east."}})
print(step.info)
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
