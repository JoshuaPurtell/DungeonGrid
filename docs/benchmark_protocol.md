# DungeonGrid Benchmark Protocol

This document defines the stable benchmark surfaces for DungeonGrid.

## Suites

### DG-Solo-20

- Quests: the 20 bundled full dungeons.
- Heroes: 1.
- Seeds: 0-9.
- Step limit: 200 environment steps per episode.
- Interface: structured JSON actions.
- Ruleset: default AP mode.

### DG-Coop-20

- Quests: the 20 bundled full dungeons.
- Heroes: 2-4.
- Seeds: 0-9.
- Step limit: 300 environment steps per episode.
- Interface: structured JSON action plans with reveal-boundary interruption.
- Ruleset: default AP mode.

### DG-Lite-20

- Quests: the 20 bundled `_lite` diagnostic dungeons.
- Heroes: recommended lite hero count from the dungeon metadata.
- Seeds: 0-9.
- Step limit: 120 environment steps per episode.
- Interface: structured JSON action plans with reveal-boundary interruption.
- Ruleset: default AP mode unless the run name explicitly includes `classic_dynamic`.

### DG-Tiered-80

- Quests: `base:<family>:pico`, `base:<family>:lite`, `base:<family>:medium`, and `base:<family>:heavy` for all 20 bundled families.
- Heroes: 1 for `pico`, 2 for `lite`, 3 for `medium`, and 4 for `heavy`.
- Seeds: 0-9.
- Step limit: 120 for `pico`/`lite`, 300 for `medium`/`heavy`.
- Interface: structured JSON action plans with reveal-boundary interruption.
- Ruleset: default AP mode unless the run name explicitly includes `classic_dynamic`.

### DG-ClassicDynamic-20

- Quests: the 20 bundled full dungeons.
- Heroes: 1-4, with quest role requirements enforced where configured.
- Seeds: 0-9.
- Step limit: 300 environment steps per episode.
- Interface: structured JSON action plans with reveal-boundary interruption.
- Ruleset: `classic_dynamic`.
- Warden: deterministic bounded Warden by default; ReAct Warden adapters are optional eval harnesses.

### DG-OpenEnv-ReAct

- Quests: full or lite suite variants.
- Heroes: 1-4 plus automatic Warden control.
- Seeds: 0-9.
- Interface: OpenEnv/ReAct-style queued JSON plans.
- Ruleset: declared by the benchmark config; default/AP and `classic_dynamic` scores are not aggregated.
- Warden: NanoCoop `dungeongrid_react` configs use first-class ReAct Warden by default; offline/reproducible suites opt out with `warden_policy.kind=deterministic_warden`.

### DG-ReAct-Warden

- Quests: full or lite suite variants.
- Heroes: 1-4 controlled by hero policies.
- Warden: private/eval ReAct policy using `dungeongrid_warden_act`.
- Interface: heroes submit queued JSON plans; Warden chooses one bounded Warden action per Warden turn.
- Required reporting: separate hero LLM usage, Warden LLM usage, Warden fallback count, Warden action counts, and Warden fairness metadata.

## Migration Note

Some internal planning notes used an older HQ-labeled draft name. The public and documented
ruleset name is `classic_dynamic`; benchmark configs and downstream harnesses should not use
the older planning name.

## Required Metrics

Every benchmark run must report:

- `dungeongrid_version`
- `suite`
- `quest_id`
- `seed`
- `num_heroes`
- `success`
- `winner`
- `total_reward`
- `normalized_reward`
- `steps`
- `rounds`
- `achievements_unlocked`
- `per_hero_stats`
- `invalid_action_count`
- `reveal_interrupt_count`
- `transcript_tokens_estimate`
- `wall_clock_seconds`

## Reward Convention

`total_reward` is a non-negative progress score. Objective completion and extraction dominate,
with smaller credit for exploration, achievements, treasure, combat progress, survival, and
useful coordination. Invalid actions, damage, bad draws, and Warden pressure are reported as
diagnostic metrics and transcript events; they do not subtract from reward.

## Stability Rule

Changes that alter benchmark scores must be called out in the changelog or release notes.
Bug fixes should include an errata note describing affected versions and whether old scores
should be considered stale.
