# DungeonGrid

DungeonGrid is a text-first cooperative dungeon-crawl environment for
multi-agent benchmarks.

![DungeonGrid solo replay](docs/assets/gpt54_nano_lantern_crypt_solo_sprite.gif)

Above: a `gpt-5.4-nano` solo OpenEnv ReAct rollout in `lantern_crypt`.

It is designed around:

- one to four submitted hero agents;
- an always-AI Warden / dungeon-controller side;
- compact text board-state observations;
- structured JSON action plans instead of string actions;
- batched OpenEnv ReAct-style plan execution with reveal-boundary replanning;
- fixed quest difficulty across solo, duo, trio, and squad slices.

This package is currently an alpha extraction of the DungeonGrid engine that is
being integrated into NanoCoop.

## Replays

DungeonGrid can export reviewable rollout artifacts as terminal-style and
sprite-style GIF/HTML replays. These are meant to make agent behavior legible:
movement, Warden turns, messages, invalid actions, achievements, card draws, and
boss/furniture events all show up beside the map.

Solo rollout:

![DungeonGrid solo sprite replay](docs/assets/gpt54_nano_lantern_crypt_solo_sprite.gif)

Duo rollout:

![DungeonGrid duo sprite replay](docs/assets/gpt54_nano_lantern_crypt_duo_sprite.gif)

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

## Achievements

DungeonGrid reports Craftax-style unique achievements as discrete progress
markers alongside scalar reward. Each achievement unlocks at most once per run,
adds a small reward bonus, and is included in step results, plan results,
observations, traces, and exported metrics.

There are two achievement layers:

- global achievements for cross-dungeon comparison, such as first door opened,
  first trap revealed, first monster defeated, objective recovered, and escape;
- quest achievements declared in each quest JSON for dungeon-specific progress
  landmarks.

```python
result = env.act_plan(actions=[{"type": "open_door", "target": "door_1"}])
print(result.new_achievements)
print(env.export_trace()["metrics"]["achievements_unlocked"])
```

Rollout helpers include a Craftax-like frequency summary:

```python
from dungeongrid.metrics import run_episode, summarize_achievement_frequencies

rollouts = [run_episode(env)]
print(summarize_achievement_frequencies(rollouts))
```

`env.export_transcript()` returns an LLM-reviewable transcript with observation
text, submitted plans, executed/skipped/unused actions, Warden events, messages,
achievement unlocks, reward deltas, and final metrics.

## Quests

Bundled alpha dungeons:

- `ashen_pantry`
- `barrow_of_the_hollow_king`
- `bells_under_blackwater`
- `black_standard_keep`
- `broken_oath_ambush`
- `cinder_exit`
- `cinder_mage_tower`
- `frost_mirror_hold`
- `glass_maze`
- `hourglass_escape`
- `iron_captive`
- `lantern_crypt`
- `lost_apprentice`
- `low_shrine_locks`
- `magistrate_gold`
- `moonblade_vault`
- `return_to_hollow_barrow`
- `trial_of_embers`
- `tusk_warlord_lair`
- `veiled_castle`

Quest authoring now uses a self-contained dungeon folder:

```text
dungeons/<dungeon_id>/
  quest.json
  hooks.py
```

`quest.json` contains the map, rooms, objective, chest/deck setup, furniture,
monster/boss config, scripts, and achievement definitions. `hooks.py` is
optional Python behavior for bespoke dungeon effects; bundled dungeons include a
hook file so every dungeon has the same shape. The current flat `quests/*.json`
files remain as a temporary compatibility fallback during the alpha transition.

Hooks register typed trigger handlers:

```python
def on_load(ctx): ...

def register(registry):
    registry.on("on_objective_taken", handler)
    registry.on("on_furniture_searched", handler)
    registry.on("on_furniture_destroyed", handler)
    registry.on("on_warden_cleanup", handler)
    registry.on("on_boss_phase_changed", handler)
    registry.on("on_boss_defeated", handler)
```

Handlers return typed effects such as `SetFlag`, `SpawnMonster`,
`UnlockAchievement`, `ModifyAlert`, and `EmitEvent`; the effect resolver is the
mutation boundary for action-time behavior.

The bundled dungeons use the richer authoring shape. `quest.json` defines room
descriptions, searchable tactical furniture, compact decks, hero loadouts,
bosses, monster activation rules, and achievements. Hooks are reserved for
bespoke pressure patterns: alarm interruption, secret-route support, boss
counterplay, escort pressure, and synchronized lock/token progress.

## Status

DungeonGrid is under active development. Public names use DungeonGrid, while
some compatibility aliases for the earlier TorchGrid prototype remain in the
Python API to ease migration.
