# DungeonGrid Plans

## Dungeon Size Tiers

DungeonGrid should treat party size as part of the benchmark contract, not as a
generic scaling knob. The current full dungeons should become the medium tier:
small enough to avoid hallway congestion, but large enough to require real
multi-agent planning. Harder four-agent play should live in a separate heavy
variant for each dungeon family.

### Target Tiers

| Tier | Agents | Scope | Purpose |
| --- | ---: | --- | --- |
| pico | 1 | 1-2 rooms, 1-2 basic challenges | Check whether a single model broadly understands the task family. |
| lite | 2 | 3-4 rooms, multiple coordination challenges | Test paired coordination without full-party congestion. |
| medium | 3 | 5-6 rooms, many challenges with hidden/stochastic elements | Main benchmark tier for normal dungeons. |
| heavy | 4 | 7-8 rooms, many hard challenges | Full-party stress tier for congestion, communication, and hard coordination. |

### Design Direction

- `pico` variants should be deliberately simple, but not trivial. Each should
  preview the larger dungeon's main lesson with one hero, one route decision,
  and one mechanic that becomes cooperative in larger variants.
- `lite` variants should remain two-agent diagnostic capsules. They should
  preserve the intended pair for the task, such as wizard plus barbarian in
  `lantern_crypt_lite`.
- `medium` should be the default/full dungeon benchmark tier and should use
  three heroes. Three agents appears to be the sweet spot for coordination
  without turning small maps into traffic puzzles. Medium should generally have
  enough branches, loops, and partially hidden side objectives that the party
  must maintain a shared plan, but it should avoid becoming a long navigation
  crawl.
- `heavy` variants should be authored separately for four heroes. They should
  intentionally test full-party traffic, message discipline, role handoffs,
  split objectives, and extraction pressure. Heavy maps should usually be larger
  than medium maps, not just denser, so the fourth hero has real work instead of
  becoming hallway congestion. Even heavy should stay compact enough that the
  benchmark measures cooperation more than map wandering.

### Content Reuse

For simplicity and consistency, each dungeon family should reuse its core
authored content across tiers:

- bosses and boss counterplay;
- monster rosters and enemy pressure patterns;
- clue objects, furniture hooks, and search categories;
- spell, item, armor, and deck identities;
- achievement themes and social metrics;
- Warden pressure runbooks.

The room maps should be explicit per tier. Dungeon geometry is too important to
let a compiler improvise it from snippets. Pico, lite, medium, and heavy should
each have hand-authored maps sized for their intended party count.

What should be reused is the symbolic content placed on those maps. A dungeon
family can define a shared catalog of objectives, bosses, monster variants,
furniture, clue objects, treasure tables, traps, achievements, and Warden
pressure patterns. Each tier-specific map then places a subset or elaboration of
that shared content.

In other words:

```text
dungeon family = shared catalog + shared hooks + tier-specific explicit maps
```

The tier maps can be nested in spirit without needing identical geometry:

- `pico` previews the core mechanic in a tiny authored layout;
- `lite` adds the first real coordination beat;
- `medium` expands into the default many-room dungeon with branching, hidden
  information, and role-specific jobs;
- `heavy` adds enough space, parallel objectives, and pressure lanes for four
  heroes to all be necessary.

Reusing the mechanic is more important than reusing the exact room geometry.

Corridors should be treated as authored gameplay space, not just connectors.
Classic dungeon-crawl tactics often happen in hallways: scouting ahead, holding a
door, blocking a pursuit lane, deciding when to open the next room, escorting an
objective carrier through a chokepoint, and managing who can see or reach a
threat. Tier budgets count rooms, but each tier should also deliberately design
corridor pressure:

- `pico`: one simple hallway or doorway teaches movement and extraction timing;
- `lite`: a corridor/doorway creates a two-hero handoff or body-blocking choice;
- `medium`: branching corridors create scouting, route choice, and pursuit
  management;
- `heavy`: multiple pressure lanes create full-party traffic and communication
  challenges without requiring a huge room count.

### Metadata Contract

Each dungeon variant should eventually declare its tier and intended party
shape explicitly:

```json
{
  "metadata": {
    "size_tier": "medium",
    "intended_num_heroes": 3,
    "supported_hero_range": [1, 3],
    "variant_family": "lantern_crypt"
  },
  "recommended_heroes_by_party_size": {
    "1": ["wizard"],
    "2": ["wizard", "barbarian"],
    "3": ["wizard", "barbarian", "dwarf"],
    "4": ["wizard", "barbarian", "elf", "dwarf"]
  }
}
```

The runtime should use `recommended_heroes_by_party_size` when present instead
of blindly taking the first N roles from `recommended_heroes`.

### Implementation Notes

- Add `pico` and `heavy` variant folders for every dungeon family.
- Retune current full dungeons to be `medium` and default to three heroes.
- Keep current `lite` dungeons focused on two heroes.
- Preserve solo support where useful, but do not force every tier to be equally
  fair for every party size.
- Add benchmark suites for `DG-Pico-20`, `DG-Lite-20`, `DG-Medium-20`, and
  `DG-Heavy-20`.
- Report tier-specific scores separately; do not aggregate pico/lite/medium/heavy
  into one headline number.

## Expansion Architecture

DungeonGrid should not use a separate "mission" abstraction. The clean hierarchy
is:

```text
core engine -> expansion -> dungeon family -> size variant
```

The core package owns shared game systems. Expansions own themed content and
dungeon families. Each dungeon family owns its pico/lite/medium/heavy variants.

### Target Layout

```text
src/dungeongrid/
  core/
    actions, state machine, effects, triggers, validation
    generic monsters, items, spells, cards, furniture, traps, bosses
    rendering, replay, OpenEnv/ReAct contracts

  expansions/
    base/
      expansion.json
      content/
        monsters.json
        items.json
        spells.json
        cards.json
        furniture.json
        bosses.json
        terrain.json
      dungeons/
        lantern_crypt/
          pico/quest.json
          lite/quest.json
          medium/quest.json
          heavy/quest.json
        cinder_mage_tower/
          pico/quest.json
          lite/quest.json
          medium/quest.json
          heavy/quest.json

    deep_gate/
      expansion.json
      content/
        monsters.json
        items.json
        spells.json
        cards.json
        furniture.json
        bosses.json
        terrain.json
      dungeons/
        breach_beneath_stonefall/
          pico/quest.json
          lite/quest.json
          medium/quest.json
          heavy/quest.json
```

Public dungeon ids should reflect this hierarchy without exposing internal file
paths. Candidate ids:

```text
base:lantern_crypt:lite
base:lantern_crypt:medium
deep_gate:breach_beneath_stonefall:medium
deep_gate:breach_beneath_stonefall:heavy
```

If `base:` feels too noisy for the default bundled set, the public API may allow
`lantern_crypt:medium` as an alias, but the canonical stored id should remain
fully qualified.

### Core Versus Expansion Content

Move mechanics into the shared core whenever they are broadly reusable:

- action validation and AP/turn/ruleset flow;
- public/private state;
- OpenEnv/ReAct hero and Warden contracts;
- movement, combat, line of sight, activation, extraction;
- generic furniture, traps, chests, cards, decks, and search categories;
- typed effects, trigger timing, boss phases, damage gates, statuses;
- common weapons, armor, spells, and reusable monster archetypes.

Keep content in an expansion when it is themed or campaign-specific:

- dungeon maps and variant-specific quest data;
- expansion-specific bosses and named enemies;
- themed monster variants;
- themed items, artifacts, terrain, clue objects, cards, and room dressing;
- expansion-level Warden runbooks and pressure hooks;
- expansion-specific achievements and social metrics.

The current bundled dungeons should become the `base` expansion. Most of their
engine behavior should move into shared core. Only base-specific bosses, clues,
achievement themes, and dungeon flavor should remain in `expansions/base`.

### Deep Gate Download Merge Direction

The downloaded Deep Gate patch should be treated as a design source, not as a
literal patch. Its useful content is:

- fortress/tunnel/gate dungeon families;
- gatekeepers, sappers, spear enemies, drum callers, abominations, and a gate
  captain boss;
- breach tools, route markers, reinforced shields, signal cloaks, pressure
  gates, rubble, reinforcement tunnels;
- collapse clocks, reinforcement pressure, route/lock progress hooks;
- MARL-focused dungeon goals such as route memory, holder/searcher assignment,
  synchronized lever work, escort extraction, and boss/chokepoint control.

The patch's `missions/` naming should not survive. Convert its content into:

```text
expansions/deep_gate/dungeons/<dungeon_family>/<tier>/quest.json
```

Start by importing one or two Deep Gate dungeon families as medium/lite examples,
then add pico/heavy variants once the architecture is stable.

## Engine + Expansion Refactor Implementation Plan

The next structural push should introduce the expansion/family/tier authoring
model before adding more content. The goal is not procedural generation. The
goal is a cleaner content boundary: explicit maps per tier, shared symbolic
catalogs per dungeon family, and expansion-level content packs.

Kickoff status: the first implementation slice should land expansion-aware
loading, package data, canonical `base:lantern_crypt:<tier>` ids, Lantern family
metadata, and the four Lantern tier quests before migrating any other dungeon
families.

### Phase 1: Loader And IDs

- Add an `expansions/` content root alongside the current flat `dungeons/`
  folder.
- Introduce canonical dungeon ids:

```text
<expansion>:<family>:<tier>
```

Examples:

```text
base:lantern_crypt:pico
base:lantern_crypt:lite
base:lantern_crypt:medium
base:lantern_crypt:heavy
```

- Keep short aliases only where useful during the migration, such as
  `lantern_crypt` -> `base:lantern_crypt:medium` and `lantern_crypt_lite` ->
  `base:lantern_crypt:lite`.
- Update `GridEngine.available_quests()` and quest loading to discover both
  expansion-style quests and legacy flat quests during the transition.
- Update package data so expansion `quest.json`, `family.json`, `hooks.py`, and
  content catalog files are included in built wheels.

### Phase 2: Family Catalog Resolution

Each dungeon family should support this shape:

```text
expansions/<expansion>/dungeons/<family>/
  family.json
  hooks.py
  pico/quest.json
  lite/quest.json
  medium/quest.json
  heavy/quest.json
```

`family.json` owns shared symbolic content:

- objective definitions;
- named monster variants;
- furniture, chests, traps, clues, and special objects;
- shared decks, cards, artifacts, weapons, armor, and spells;
- shared achievements and social metrics;
- shared Warden runbook notes;
- shared role-demand vocabulary.

Each tier `quest.json` owns:

- explicit authored ASCII map;
- party size and recommended roles;
- tier-specific placements that reference family catalog entries;
- tier-specific role demands and coordination demands;
- tier-specific rewards, achievements, pressure, and extraction rules.

The loader should resolve tier placements against the family catalog and produce
the concrete quest shape the runtime already understands.

### Phase 3: Validation

Add a content validator before broad migration. It should check:

- every canonical dungeon id is unique;
- every tier map is rectangular and parseable;
- every placement reference exists in `family.json` or expansion content;
- every configured hero has at least one declared role demand;
- intended hero count matches the tier budget;
- objective and extraction tiles exist;
- required hooks exist and use supported trigger names;
- public metadata does not expose private inspiration notes;
- package data includes every expansion file required at runtime.

The validator should make authoring safer without requiring every map to be
procedurally generated or inferred.

### Phase 4: Runtime Compatibility

- Keep the core state machine, effects, triggers, public/private observations,
  ReAct hero policy, ReAct Warden surface, rendering, traces, checkpoints, and
  achievements in shared core.
- Make expansion content data-only where possible.
- Allow family `hooks.py` for memorable boss, clue, Warden, or extraction
  behavior that is awkward to express in JSON.
- Preserve public APIs such as `reset`, `act_plan`, `public_state_json`,
  `private_state_json`, and NanoCoop integration.

## Lantern Crypt Refactor Proving Slice

After the general loader/catalog refactor exists, Lantern Crypt should be the
first fully migrated family. It should prove the new authoring model before all
other dungeons move.

### Target Structure

```text
src/dungeongrid/expansions/base/dungeons/lantern_crypt/
  family.json
  hooks.py
  pico/quest.json
  lite/quest.json
  medium/quest.json
  heavy/quest.json
```

### Shared Family Identity

Lantern Crypt should keep the same recognizable benchmark identity across all
tiers:

- recover the ember idol and extract through the entrance;
- optional greed via chest/treasure search;
- pursuit pressure after objective pickup;
- altar/clue counterplay that weakens or explains the wight;
- role-specific help from weapons, traps/secrets, spells, and corridor control;
- Warden pressure focused on carrier pursuit, split-party punishment, and
  extraction timing.

Shared catalog entries should include:

- `ember_idol` objective;
- `ember_altar` clue/counterplay furniture;
- `weapon_rack` gear object;
- `crypt_chest` treasure-risk object;
- `needle_trap` or equivalent trap;
- `lantern_wight` boss-like pursuer;
- `crypt_guard`, `rat_pressure`, and `hollow_guard` monster variants;
- `lantern_treasure` and optional `ember_event` deck;
- achievements for recovering the idol, reading the altar, escaping with the
  idol, sharing useful gear, and managing pursuit.

### Tier Maps

The tier maps should be explicit, compact, and corridor-aware:

- `pico`: 1 hero, 1-2 rooms plus one doorway/corridor timing beat.
- `lite`: 2 heroes, 3-4 rooms plus a corridor handoff or body-blocking choice.
- `medium`: 3 heroes, 5-6 rooms plus branching corridors, search/counterplay,
  and extraction route planning.
- `heavy`: 4 heroes, 7-8 rooms plus multiple pressure lanes, carrier escort,
  split search, and Warden pressure.

The maps should feel like variants of the same dungeon family, but they do not
need identical geometry. Reuse symbolic content and challenge identity, not the
exact room layout.

### Role Demands

Each Lantern tier should state why its configured heroes are needed:

- pico: single hero can complete the basic retrieve/extract loop.
- lite: one hero handles carrier/search timing while the other controls pursuit
  or prepares gear.
- medium: barbarian controls enemies/chokepoints, wizard resolves altar or spell
  counterplay, dwarf handles traps/secrets/safe searches.
- heavy: barbarian holds pursuit lanes, wizard manages magical counterplay, elf
  scouts/heals/supports carrier movement, dwarf handles traps/secrets/search
  safety.

The validator should reject or warn on a tier where a configured hero has no
declared role demand.

### Success Criteria

The Lantern Crypt migration is complete when:

- all four canonical ids load:
  - `base:lantern_crypt:pico`
  - `base:lantern_crypt:lite`
  - `base:lantern_crypt:medium`
  - `base:lantern_crypt:heavy`
- legacy aliases route to the intended tier during transition;
- public observations, traces, checkpoints, terminal replay, and sprite replay
  still work;
- role recommendations use `recommended_heroes_by_party_size`;
- all four tiers expose appropriate achievements and per-hero stats;
- NanoCoop can run pico/lite/medium/heavy through the same DungeonGrid adapter.

## Dungeon Family Tier Backlog

After Lantern Crypt proves the expansion/family/tier model, every other current
base dungeon family should get the same treatment. The backlog below is
intentionally TODO-oriented: each family needs a shared `family.json`, explicit
pico/lite/medium/heavy maps, role demands for every configured hero, corridor
pressure, achievements, and Warden pressure notes.

### Migration Checklist Per Family

- [ ] Create `expansions/base/dungeons/<family>/family.json`.
- [ ] Move or rewrite current full dungeon as `<family>/medium/quest.json`.
- [ ] Move or rewrite current lite dungeon as `<family>/lite/quest.json`.
- [ ] Add `<family>/pico/quest.json` for one-agent capability probing.
- [ ] Add `<family>/heavy/quest.json` for four-agent full-party pressure.
- [ ] Declare `recommended_heroes_by_party_size`.
- [ ] Declare role demands for every supported hero count.
- [ ] Declare corridor pressure and room count target for each tier.
- [ ] Validate objective/extraction, achievements, hooks, render symbols, and
  public/private state redaction.

### Base Dungeon Family TODOs

- [ ] `ashen_pantry`
  - Theme: pantry/goblin pressure, early survivability, simple greed.
  - Tier work: define a clean pico food-cache loop, keep lite as two-agent
    split/search pressure, make medium a three-hero route/search/fight task, and
    reserve heavy for multi-lane rat/goblin pressure.
- [ ] `barrow_of_the_hollow_king`
  - Theme: undead revive/counterplay, lore clue, objective extraction.
  - Tier work: scale hollow-knight counterplay from a single clue in pico to
    heavy's multi-guard tomb with role-specific banish/search/fight jobs.
- [ ] `bells_under_blackwater`
  - Theme: noise discipline, bell/event pressure, careful movement.
  - Tier work: make each tier explicitly teach when to move, search, or delay;
    heavy should require distributed noise control and extraction timing.
- [ ] `black_standard_keep`
  - Theme: fortress pressure, doorway control, blocker/brute contrast.
  - Tier work: preserve the keep identity while making pico a single breach,
    lite a two-lane hold, medium a three-role assault, and heavy a full
    defender/standard extraction problem.
- [ ] `broken_oath_ambush`
  - Theme: ambush recognition, rescue/escape, sudden Warden pressure.
  - Tier work: make smaller tiers teach survival and regrouping; medium/heavy
    should require communication about revealed threats and escape lanes.
- [ ] `cinder_exit`
  - Theme: exit pressure, cinder/fire hazard, timed extraction.
  - Tier work: size each tier around a different extraction route puzzle with
    explicit carrier/support/guard responsibilities.
- [ ] `cinder_mage_tower`
  - Theme: caster pressure, spell counterplay, furnace/focus mechanics.
  - Tier work: keep the polished tower mechanics as shared catalog content, then
    make pico/lite teach caster line-of-sight and medium/heavy require planned
    spell/furniture counterplay.
- [ ] `frost_mirror_hold`
  - Theme: mirror/frost misdirection, route memory, split observation.
  - Tier work: make the smaller tiers teach mirror affordances; medium/heavy
    should stress shared route memory and decoy/counterplay coordination.
- [ ] `glass_maze`
  - Theme: mirror adept, decoy punishment, navigation under partial observability.
  - Tier work: keep maze size compact but corridor-rich; every tier should make
    decoy handling and route communication visible in traces.
- [ ] `hourglass_escape`
  - Theme: time pressure, reversal/return route, extraction urgency.
  - Tier work: tier by clock complexity rather than map sprawl; heavy should
    require parallel preparation before the final escape push.
- [ ] `iron_captive`
  - Theme: escort/protect specialist, captive extraction, body-blocking.
  - Tier work: make pico a tiny escort, lite a protector/escort pair, medium a
    three-role route-clear/extract task, and heavy a multi-lane escort under
    Warden pressure.
- [ ] `low_shrine_locks`
  - Theme: shrine locks, specialist actions, sentinel/blocker pressure.
  - Tier work: encode synchronized lock handling and ensure each party size has
    a real lock/guard/route job rather than idle extra heroes.
- [ ] `magistrate_gold`
  - Theme: greed accounting, treasure risk, Warden dread.
  - Tier work: make greed consequences clear at every tier; heavy should support
    distributed treasure search with visible social metrics for hoarding/sharing.
- [ ] `moonblade_vault`
  - Theme: artifact vault, role-gated approach, magical/melee handoff.
  - Tier work: identify the core vault mechanic, then scale from one clear vault
    task to heavy's multi-key artifact extraction.
- [ ] `return_to_hollow_barrow`
  - Theme: revisiting undead pressure with stronger counterplay expectations.
  - Tier work: use it as a harder sibling of `barrow_of_the_hollow_king`; pico
    should still be simple, while medium/heavy assume players know revive clues.
- [ ] `trial_of_embers`
  - Theme: trial rooms, fire/ember tests, staged cooperation.
  - Tier work: map each tier to a clear number of trials and require different
    heroes to lead different trial beats.
- [ ] `tusk_warlord_lair`
  - Theme: war drum, brute/mauler pressure, boss counterplay.
  - Tier work: keep drum/trophy/furniture mechanics shared; scale from one boss
    lesson in pico to heavy's full lair with alarm, cleave, and escape pressure.
- [ ] `veiled_castle`
  - Theme: partial-observation finale, composition challenge, hidden routes.
  - Tier work: preserve it as a higher-complexity family; pico/lite should teach
    veil/route ideas, while medium/heavy become capstone coordination tasks.

Lantern Crypt remains the first proving slice. These families should not be
bulk-migrated until the Lantern loader/catalog/validator path is working.
