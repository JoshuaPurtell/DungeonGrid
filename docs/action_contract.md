# DungeonGrid Action Contract

Agents submit exact structured JSON actions. They do not receive legal-action lists in public
observations; the environment validates actions and reports invalid feedback in the next state.

Common action shapes:

```json
{"type": "move", "direction": "east"}
{"type": "open_door", "target": "door_1"}
{"type": "attack_melee", "target": "bone_guard_1"}
{"type": "attack_ranged", "target": "cinder_mage_1"}
{"type": "cast", "target": "bone_guard_1", "payload": {"spell": "spark_lance"}}
{"type": "search_treasure", "target": "chest_1"}
{"type": "search_furniture", "target": "altar_1"}
{"type": "give_item", "target": "hero_2", "payload": {"item": "shield"}}
{"type": "message", "target": "party", "payload": {"text": "I will hold the door."}}
{"type": "call_extraction"}
{"type": "end_turn"}
```

`act_plan(actions, intent=None, agent_id=None)` executes queued actions in order, skips invalid
actions, and stops when a reveal boundary or turn boundary requires replanning.

`classic_dynamic` adds roll-to-move, one major action per hero turn, safe-room search gating,
risky treasure, Warden dread, and extraction choices.

Environment-controlled Warden actions are internal/eval actions, not player actions:

```json
{"type": "warden_auto"}
{"type": "warden_spend_dread", "target": "hero_1", "payload": {"effect": "spawn_wanderer"}}
{"type": "activate_monster", "target": "bone_guard_1"}
```

Optional Warden ReAct harnesses must choose from bounded Warden candidates and route the result
through normal environment validation.
