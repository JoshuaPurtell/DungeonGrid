# DungeonGrid Observation Contract

DungeonGrid separates public state from private state.

Public observations may include:

- active hero identity, role, HP, AP, movement, statuses, and equipment;
- visible map and visible rooms;
- visible entities and visible objects;
- party roster and visible teammate summaries;
- recent events, party messages, known card draws, invalid feedback, and achievements.

Public observations must not include:

- legal-action lists;
- hidden deck order;
- unopened chest contents;
- unrevealed trap positions;
- dormant hidden monsters;
- private furniture effects or hook internals;
- Warden-only state such as full hidden pressure plans.

Use `public_state_json()` for player-facing/replay state and `private_state_json()` for debug,
evaluation, and deterministic package checks.

Use `observe_warden()` only for private/eval Warden policies. It may include Warden candidates,
revealed-state pressure context, MARL metadata, dread, and recent party actions; it is not a
player observation and should not be exposed to hero agents.
