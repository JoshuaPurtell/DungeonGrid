# Dungeon Authoring

Bundled dungeons live under `src/dungeongrid/dungeons/<quest_id>/`.

Required:

- `quest.json`

Optional:

- `hooks.py`
- `README.md`

`quest.json` defines map ASCII, rooms, objective, recommended heroes, monsters, doors, traps,
chests, furniture, decks, achievements, metadata, mechanics, and optional `classic_dynamic`
ruleset hints.

Use JSON effect lists for most behavior. Use `hooks.py` only for memorable dungeon-specific
logic that cannot be expressed cleanly with typed effects and trigger registration.

Every dungeon should load with solo, duo, trio, and squad party sizes unless it intentionally
documents a specialist role requirement for a benchmark slice.

## Classic Dynamic Recipe

For `classic_dynamic`, add or verify:

- `metadata.marl_axis` and `metadata.coordination_type`;
- `metadata.classic_dynamic_role_dilemma`;
- `metadata.classic_dynamic_warden_pressure`;
- `metadata.classic_dynamic_extraction_hook`;
- `mechanics.marl_contract` with the benchmark failure modes;
- `mechanics.warden_policy` with preferred and forbidden pressure patterns;
- `ruleset.classic_dynamic_available = true`;
- optional `role_selection.required_roles_by_party_size` for hard benchmark gates.

Default/AP mode treats role requirements as soft warnings. `classic_dynamic` treats configured
requirements as hard validation so benchmark slices have stable party composition.

Warden ReAct harnesses should use the package Warden observation/adapter surface and still route
all chosen actions through environment legality checks.
