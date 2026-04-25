# DungeonGrid MARL Dungeon Curriculum

This patch turns the bundled dungeon set into an explicit multi-agent reinforcement-learning curriculum. The design goal is not to add random variants; it is to make every dungeon feel like an authored story that isolates a recognizable MARL failure mode.

Each dungeon now receives a per-dungeon README describing:

- theme and story identity;
- primary MARL axis;
- concrete challenges posed to hero agents;
- dilemmas, tradeoffs, and failure modes;
- the multi-agent coordination problem it is meant to expose;
- Warden ReAct runbook notes;
- a compact lite variant for 1-2 hero rollouts.

The lite variants are new runnable quest folders named `<quest_id>_lite`. They use the existing `quest.json` folder convention, so the current `GridEngine.available_quests()` and `GridEngine.load_quest_data()` path should discover them without loader changes.

## Curriculum matrix

| Full quest | Lite quest | Act | MARL axis | Coordination type | Lite heroes |
|---|---|---:|---|---|---|
| `ashen_pantry` | `ashen_pantry_lite` | I | decentralized task allocation under costly search | divide-and-report exploration | elf, dwarf |
| `barrow_of_the_hollow_king` | `barrow_of_the_hollow_king_lite` | III | credit assignment for delayed maintenance tasks | fight-cleanse-guard rotation | dwarf, wizard |
| `bells_under_blackwater` | `bells_under_blackwater_lite` | I | shared global externality management | team alert-budget discipline | wizard, elf |
| `black_standard_keep` | `black_standard_keep_lite` | III | opponent-aware breach sequencing | threshold control against a tactical defender | barbarian, elf |
| `broken_oath_ambush` | `broken_oath_ambush_lite` | II | contingency planning under hidden threat | bait-cover-fallback protocol | barbarian, dwarf |
| `cinder_exit` | `cinder_exit_lite` | II | cooperative extraction under pursuit | carrier escort and rear-guard handoff | elf, barbarian |
| `cinder_mage_tower` | `cinder_mage_tower_lite` | III | target priority with asymmetric threat ranges | covering advance against ranged control | wizard, barbarian |
| `frost_mirror_hold` | `frost_mirror_hold_lite` | II | belief-state fusion under decoys | shared observation and verification | elf, wizard |
| `glass_maze` | `glass_maze_lite` | II | shared map memory and route compression | scout-report-map-update loop | elf, dwarf |
| `hourglass_escape` | `hourglass_escape_lite` | IV | decentralized scheduling under deadline | timed route and objective sequencing | elf, barbarian |
| `iron_captive` | `iron_captive_lite` | II | escort and protection of constrained third-party state | front-guard rear-guard rescue formation | barbarian, dwarf |
| `lantern_crypt` | `lantern_crypt_lite` | I | role-specialized causal counterplay | support action before damage commitment | wizard, barbarian |
| `lost_apprentice` | `lost_apprentice_lite` | II | fragile escort with communication-dependent calming | find-calm-guide extraction | elf, wizard |
| `low_shrine_locks` | `low_shrine_locks_lite` | II | joint-action synchronization | ready-check and simultaneous activation | dwarf, elf |
| `magistrate_gold` | `magistrate_gold_lite` | II | mixed-motive sequential social dilemma | shared inventory accounting | dwarf, elf |
| `moonblade_vault` | `moonblade_vault_lite` | III | heterogeneous role-task assignment | scout-disarm-handoff | elf, dwarf |
| `return_to_hollow_barrow` | `return_to_hollow_barrow_lite` | IV | transfer and adaptation to a changed environment | reuse old policy while noticing changed dynamics | barbarian, wizard |
| `trial_of_embers` | `trial_of_embers_lite` | IV | multi-objective sequencing with non-dominant strategies | proof selection and resource preservation | wizard, dwarf |
| `tusk_warlord_lair` | `tusk_warlord_lair_lite` | III | formation control against cleave pressure | frontline pin with ranged spacing | barbarian, elf |
| `veiled_castle` | `veiled_castle_lite` | IV | compositional partial-observation final | belief, clue, counterplay, and extraction composition | elf, wizard |

## Global design contract

Each quest should be interpreted through these fields in `metadata` and `mechanics`:

```json
{
  "metadata": {
    "marl_axis": "the primary multi-agent challenge",
    "coordination_type": "the intended joint-policy shape",
    "information_structure": "decentralized_partial_observation",
    "reward_structure": "shared_team_reward_with_optional_individual_temptations",
    "warden_pressure_model": "text_runbook_react_agent",
    "coordination_problems": [],
    "dilemmas": [],
    "warden_runbook": []
  },
  "mechanics": {
    "marl_contract": {
      "axis": "...",
      "tags": [],
      "core_failure_modes": []
    },
    "warden_policy": {
      "hidden_information_access": "revealed_state_plus_authored_dungeon_memory",
      "pressure_budget_per_round": 1,
      "preferred_tactics": [],
      "forbidden_tactics": []
    }
  }
}
```

The engine already copies `metadata` and `mechanics` into `state.scripts`, so a Warden adapter or evaluation harness can read these contracts from state without introducing a new runtime dependency.

## Lite variant principles

Lite variants are designed for smaller LLMs and faster rollouts:

1. 2-4 rooms.
2. 1-2 recommended heroes.
3. One primary MARL axis.
4. One optional temptation or side route.
5. Short extraction after objective pickup.
6. No custom hooks required for baseline play.
7. Warden pressure constrained to a one-budget, theme-specific runbook.

They are not meant to replace the full dungeons. They are small diagnostic probes: fast to run, easy to review in transcript form, and easy to use for ablations.

## MARL coverage

- **Decentralized partial observability:** `frost_mirror_hold`, `glass_maze`, `veiled_castle`.
- **Communication and belief-state fusion:** `glass_maze`, `frost_mirror_hold`, `low_shrine_locks`.
- **Credit assignment and support-role valuation:** `lantern_crypt`, `barrow_of_the_hollow_king`, `return_to_hollow_barrow`.
- **Sequential social dilemmas:** `bells_under_blackwater`, `magistrate_gold`, `ashen_pantry`.
- **Heterogeneous role assignment:** `moonblade_vault`, `trial_of_embers`, `cinder_mage_tower`.
- **Opponent modeling / non-stationarity:** `black_standard_keep`, `tusk_warlord_lair`, `veiled_castle`.
- **Scheduling and dynamic routing:** `hourglass_escape`, `cinder_exit`, `iron_captive`.
- **Formation and spatial coordination:** `tusk_warlord_lair`, `black_standard_keep`, `cinder_exit`.
- **Transfer and compositionality:** `return_to_hollow_barrow`, `trial_of_embers`, `veiled_castle`.

## Safety / originality note

The curriculum is framed around abstract cooperative dungeon-crawl dynamics: hidden information, doors, traps, objectives, search, communication, role specialization, and an adversarial dungeon-controller policy. It avoids copying protected quest text, exact map geometry, encounter placement, proper nouns, or trade dress from any commercial game.
