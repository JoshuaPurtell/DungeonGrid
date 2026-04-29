# Goblin Mode Dungeon Catalog

This catalog adds nine second-wave Goblin Mode dungeon families. Each family has `pico`, `lite`, `medium`, and `heavy` tiers and is designed around multi-agent coordination rather than direct combat.

All dungeons use dwarven defenders as nonlethal opponents: successful goblin runs should reward sneaking, sabotage, misdirection, trapcraft, route blocking, and careful extraction timing.

| Family | Coordination focus | Goblin aesthetic |
| --- | --- | --- |
| `mushroom_sluice` | crawl-space scouting, valve timing, wet-noise masking, and split-lane extraction | glowing mushrooms, waxed grates, wet rope, stolen crumbs, and ankle-deep dwarven runoff |
| `beardglass_lampworks` | light-cone avoidance, rune-lamp sabotage, mirror-route handoffs, and synchronized scouting | brass lanterns, soot-black mirrors, stolen wick wax, purple boggart shadows, and dwarf beardglass prisms |
| `coalwhisper_kitchens` | food distractions, greasy route control, pantry looting, and quiet passage through crowded service rooms | stolen cheese, soot pots, mushroom gravy, clattering copper, and goblin snack-tax nonsense |
| `tinwhistle_lockhouse` | door timing, key routing, fake prisoner noises, and divided jail corridors | ringing keyhooks, low cell doors, stolen lock oil, goblin chalk marks, and whispering jail vents |
| `underbell_belfry` | alarm suppression, rope cutting, vertical chokepoints, and synchronized bell silencing | huge under-mountain bells, frayed ropes, mushroom wax, goblin knots, and purple false echoes |
| `slagpump_works` | machine noise, rotating valves, steam cover, and delayed defender response | slag pipes, hot rivets, wet stone, goblin soot handprints, and stolen pump grease |
| `rustsprocket_armory` | weapon-rack hazards, shield-wall bypassing, noisy forge suppression, and tactical loot denial | stolen bolts, goblin dents in polished shields, oily forge smoke, and racks of dwarf-sized inconvenience |
| `rookery_cipher_nest` | messenger interception, bird-spook discipline, route concealment, and courier timing | angry mountain crows, wax seals, stolen quills, goblin feather cloaks, and purple whisper charms |
| `nine_nails_treasury` | vault locks, pressure plates, decoy loot, exact extraction timing, and multi-role trap discipline | brass nail crowns, tiny goblin lock picks, cursed purple coin smoke, mushroom wax seals, and too many shiny things |

## Multi-agent design notes

The nine dungeons intentionally pressure different communication patterns: split-route scouting, simultaneous alarm suppression, carrier handoff decisions, optional-loot greed, trap specialist routing, and nonlethal blocker control.

The preferred four-agent party remains `goblin_scout`, `ogre_bruiser`, `kobold_tinkerer`, and `boggart_trickster`. Smaller tiers preserve the same ideas with fewer hard dependencies so benchmark runs can scale by party size.
