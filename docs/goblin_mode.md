# Goblin Mode

Goblin Mode is an inverted DungeonGrid content mode. The player-controlled party is a monster crew (`goblin_scout`, `ogre_bruiser`, `kobold_tinkerer`, and `boggart_trickster`) raiding a dwarven hold.

`game_mode` is intentionally separate from `ruleset`: the same goblin quest can run in default AP mode or `classic_dynamic` mode. The mode owns presentation labels, glyphs, role display names, quest brief language, and zero-HP narration.

Dwarven defenders are not killed. When a defender reaches 0 HP, the engine applies the `knocked_out` status, removes that defender from active combat, and emits knockout narration. This keeps the mechanics compatible with classic DungeonGrid while avoiding lethal language for the dwarven opposition.

Example:

```python
from dungeongrid import DungeonGridEnvironment

env = DungeonGridEnvironment()
obs = env.reset(
    quest_id="goblin:ironroot_hold:lite",
    num_heroes=2,
    hero_roles=["goblin_scout", "ogre_bruiser"],
    ruleset="classic_dynamic",
)
```
