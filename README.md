# DungeonGrid

DungeonGrid is a multi-agent benchmark for LLMs.

![DungeonGrid solo sprite replay](docs/assets/gpt54_nano_lantern_crypt_solo_sprite.gif)

![DungeonGrid duo sprite replay](docs/assets/gpt54_nano_lantern_crypt_duo_sprite.gif)

## OpenEnv ReAct Example

Agents receive compact text state, may query rule details, and submit structured JSON action plans. Public observations do not expose legal actions; DungeonGrid validates proposed actions, skips invalid queued actions, and reports concrete feedback in later observations.

```python
from dungeongrid import DungeonGridEnvironment, dungeongrid_rules

env = DungeonGridEnvironment()
obs = env.reset(quest_id="lantern_crypt", num_heroes=2, seed=1)

print(obs.text)
print(dungeongrid_rules("movement"))

result = env.act_plan(
    intent="Scout east, then tell the party what changed.",
    actions=[
        {"type": "move", "direction": "east"},
        {
            "type": "message",
            "target": "party",
            "payload": {"text": "I am checking the east passage."},
        },
    ],
)

print(result.executed_actions)
print(result.skipped_actions)
print(result.observation.text)
```

Tool-call shape:

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

Reveal boundaries stop queued execution so the agent can replan after meaningful new board state appears: opened doors, revealed traps, opened chests, objective changes, turn end, or episode end.

## Dungeons

Bundled dungeons use a folder-per-dungeon schema:

```text
dungeons/<dungeon_id>/
  quest.json
  hooks.py
```

`quest.json` defines the map, rooms, objective, decks, furniture, monsters, bosses, scripts, and achievements. `hooks.py` is optional Python for bespoke trigger/effect behavior.
