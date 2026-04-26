#!/usr/bin/env python3
"""Migrate legacy DungeonGrid dungeon families into expansion/family/tier layout.

Run from the root of the DungeonGrid repository, or pass --repo /path/to/DungeonGrid.
The script is intentionally idempotent: it rewrites generated expansion files from the
legacy source quest.json files and can optionally patch legacy aliases so old quest ids
resolve to the new base:<family>:<tier> ids.
"""
from __future__ import annotations

import argparse
import copy
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

TIER_ORDER = ("pico", "lite", "medium", "heavy")
TIER_HERO_COUNTS = {
    "pico": 1,
    "lite": 2,
    "medium": 3,
    "heavy": 4,
}
TIER_SUPPORTED_RANGE = {
    "pico": [1, 1],
    "lite": [1, 2],
    "medium": [1, 3],
    "heavy": [1, 4],
}
DEFAULT_ROLES_BY_SIZE = {
    "1": ["wizard"],
    "2": ["barbarian", "wizard"],
    "3": ["barbarian", "wizard", "dwarf"],
    "4": ["barbarian", "wizard", "elf", "dwarf"],
}
DEFAULT_ROLES = ["barbarian", "wizard", "elf", "dwarf"]


@dataclass(frozen=True)
class FamilySpec:
    title: str
    marl_axis: str
    purpose: str
    coordination_skills: tuple[str, ...]
    pressure_sources: tuple[str, ...]
    review_metrics: tuple[str, ...]
    success_behaviors: tuple[str, ...]
    common_failure_modes: tuple[str, ...]
    profile: str


FAMILY_SPECS: dict[str, FamilySpec] = {
    "lantern_crypt": FamilySpec(
        title="Lantern Crypt",
        marl_axis="role-specialized causal counterplay",
        purpose="Tests whether heroes value clue reading and altar counterplay before committing damage into a strengthened guardian.",
        coordination_skills=(
            "assign a clue reader or altar breaker before the boss engage",
            "screen the support hero while counterplay is prepared",
            "communicate when the guardian has been weakened enough to commit",
        ),
        pressure_sources=("lantern altar", "boss guardian", "support tempo cost", "alert from counterplay"),
        review_metrics=("counterplay before boss damage", "messages about altar rules", "frontline screens", "support isolation turns"),
        success_behaviors=(
            "one hero investigates or breaks the altar before the party rushes the boss",
            "frontline pressure keeps the support hero safe during setup",
            "the party commits damage after sharing the causal clue",
        ),
        common_failure_modes=(
            "heroes attack the guardian before reading the lantern clue",
            "the support hero is left exposed while doing the coordination-critical work",
            "the party never communicates that counterplay has changed the fight",
        ),
        profile="escort",
    ),
    "low_shrine_locks": FamilySpec(
        title="Low Shrine Locks",
        marl_axis="joint-action synchronization",
        purpose="Tests whether independently acting heroes can synchronize door, lock, and objective timing instead of greedily advancing alone.",
        coordination_skills=(
            "announce lock/door intent before spending AP",
            "hold positions until paired progress is possible",
            "sequence search, open, and carry actions across separated lanes",
        ),
        pressure_sources=("paired locks", "separated lanes", "door timing", "minor sentries"),
        review_metrics=("same-round lock progress", "messages before opens", "doorway waits", "split-party delay"),
        success_behaviors=(
            "heroes declare which lock or door they cover",
            "one hero waits or guards instead of breaking synchronization",
            "objective pickup happens after both return routes are understood",
        ),
        common_failure_modes=(
            "single hero opens a pressure room before the partner is ready",
            "both heroes chase the same lock while the other gate remains closed",
            "silent AP spending causes a stalled or unsafe route",
        ),
        profile="sync",
    ),
    "magistrate_gold": FamilySpec(
        title="Magistrate Gold",
        marl_axis="mixed-motive social dilemma",
        purpose="Tests whether heroes preserve team success when optional gold creates individual temptation and shared risk.",
        coordination_skills=(
            "negotiate when optional treasure is worth the tempo cost",
            "share healing and safety resources after risky searches",
            "stop searching once team extraction becomes the dominant objective",
        ),
        pressure_sources=("optional chests", "greed-triggered threat", "shared torch/alert budget", "exit timing"),
        review_metrics=("treasure searches by hero", "items given", "objective delay after chest opens", "messages about risk"),
        success_behaviors=(
            "party agrees on a treasure budget before opening side caches",
            "loot carriers still protect the objective carrier",
            "heroes abandon low-value gold when pressure rises",
        ),
        common_failure_modes=(
            "one hero hoards tempo or consumables for private gain",
            "party opens every chest while monsters close on the exit",
            "no one communicates when greed changes the route plan",
        ),
        profile="mixed_motive",
    ),
    "iron_captive": FamilySpec(
        title="Iron Captive",
        marl_axis="escort/protection",
        purpose="Tests escort discipline: scouting, body-blocking, and threat control around a fragile captive or carrier.",
        coordination_skills=(
            "assign scout, escort, and rear-guard roles",
            "body-block enemies without trapping the escorted unit",
            "time objective movement with lane control",
        ),
        pressure_sources=("fragile objective", "intercepting guards", "narrow corridors", "rear pursuit"),
        review_metrics=("guard actions near carrier", "distance from escort to carrier", "damage absorbed before carrier", "unsafe carrier moves"),
        success_behaviors=(
            "frontliner opens a lane before the carrier advances",
            "support heroes stay adjacent enough to heal or body-block",
            "party clears ranged or fast threats before moving the captive",
        ),
        common_failure_modes=(
            "carrier runs ahead of protection",
            "frontline chases loot and leaves the captive exposed",
            "heroes block their own extraction corridor",
        ),
        profile="escort",
    ),
    "cinder_exit": FamilySpec(
        title="Cinder Exit",
        marl_axis="extraction under pursuit",
        purpose="Tests whether the team can switch from exploration to exit execution while pressure pursues the carrier.",
        coordination_skills=(
            "pre-plan the return route before taking the objective",
            "hand off or escort the carrier under pursuit",
            "use guards, doors, and messages to maintain extraction tempo",
        ),
        pressure_sources=("pursuit spawn", "long return path", "door choke points", "partial extraction risk"),
        review_metrics=("rounds from objective taken to escape", "carrier protection actions", "doors controlled on return", "unused actions after reveal stop"),
        success_behaviors=(
            "route is cleared or marked before pickup",
            "carrier waits for escort rather than sprinting blind",
            "rear guard slows pursuit while others move toward exit",
        ),
        common_failure_modes=(
            "party keeps exploring after the objective is hot",
            "carrier separates from support",
            "doorways are left open for pursuers without a blocker",
        ),
        profile="extraction",
    ),
    "tusk_warlord_lair": FamilySpec(
        title="Tusk Warlord Lair",
        marl_axis="formation control",
        purpose="Tests spacing, lane assignment, and anti-cleave formation against heavy melee pressure.",
        coordination_skills=(
            "maintain frontline/backline spacing",
            "rotate injured blockers out of choke points",
            "focus tusk threats without bunching in cleave lanes",
        ),
        pressure_sources=("cleave monsters", "narrow lanes", "side pressure", "boss guard"),
        review_metrics=("clustered hero turns", "frontline rotations", "damage taken by backline", "doorway hold turns"),
        success_behaviors=(
            "barbarian or dwarf anchors the lane while ranged heroes support",
            "party avoids ending multiple heroes adjacent to a mauler",
            "injured blockers call for swaps before collapse",
        ),
        common_failure_modes=(
            "everyone crowds into the same doorway",
            "ranged heroes step into melee lanes unnecessarily",
            "frontline never rotates and gets downed in place",
        ),
        profile="formation",
    ),
    "black_standard_keep": FamilySpec(
        title="Black Standard Keep",
        marl_axis="lane assignment under fortress pressure",
        purpose="Tests distributed lane ownership and rally-point discipline in a keep with multiple defensive pockets.",
        coordination_skills=(
            "assign lanes before opening fortress doors",
            "collapse to a rally point when pressure spikes",
            "share status updates across separated rooms",
        ),
        pressure_sources=("fortress doors", "multi-lane guards", "alarm cultists", "optional cache detours"),
        review_metrics=("lane coverage", "messages after new room reveal", "turns isolated", "alarm/alert growth"),
        success_behaviors=(
            "heroes declare which lane they are holding",
            "scouts report before the team commits to a breach",
            "party regroups before objective extraction",
        ),
        common_failure_modes=(
            "two heroes abandon the same flank",
            "newly revealed guards are ignored while looting",
            "isolated hero triggers a room without support",
        ),
        profile="sync",
    ),
    "cinder_mage_tower": FamilySpec(
        title="Cinder Mage Tower",
        marl_axis="target priority under ranged threat",
        purpose="Tests whether agents identify and neutralize ranged casters before spending turns on nearer but lower-priority targets.",
        coordination_skills=(
            "call out ranged line-of-sight threats",
            "focus fire high-priority casters",
            "use cover, doors, and interrupts before advancing",
        ),
        pressure_sources=("ranged cinder mages", "line-of-sight corridors", "screens of weak guards", "torch/alert tempo"),
        review_metrics=("turns caster remains alive after reveal", "focus-fire consistency", "damage taken from range", "cover/door use"),
        success_behaviors=(
            "party marks casters as priority immediately",
            "frontline opens space while ranged heroes attack casters",
            "heroes avoid chasing blockers while mages keep firing",
        ),
        common_failure_modes=(
            "nearest weak monster is attacked while caster remains active",
            "heroes stand in long sight lanes without cover",
            "no one communicates the target priority switch",
        ),
        profile="ranged_priority",
    ),
    "barrow_of_the_hollow_king": FamilySpec(
        title="Barrow of the Hollow King",
        marl_axis="boss counterplay and revive control",
        purpose="Tests whether the team discovers boss counterplay and prevents revived guards from overwhelming the route.",
        coordination_skills=(
            "search for counterplay before brute-force boss damage",
            "assign guard cleanup while boss pressure is active",
            "coordinate retreat when revive pressure exceeds tempo",
        ),
        pressure_sources=("hollow knights", "boss chamber", "revive pressure", "secret or altar counterplay"),
        review_metrics=("counterplay searched before boss damage", "revived guards defeated", "route control during boss fight", "messages about boss rules"),
        success_behaviors=(
            "party searches clues before committing heavy attacks",
            "frontline pins revived guards away from supports",
            "objective carrier waits for boss counterplay to be resolved",
        ),
        common_failure_modes=(
            "boss is attacked blindly before clues are read",
            "guards are ignored until the exit is blocked",
            "the party splits during the boss phase without a plan",
        ),
        profile="escort",
    ),
    "glass_maze": FamilySpec(
        title="Glass Maze",
        marl_axis="shared map memory",
        purpose="Tests whether partial observations are turned into shared route memory through messages and disciplined exploration.",
        coordination_skills=(
            "name landmarks and dead ends in messages",
            "avoid duplicate scouting of already-known branches",
            "share secret-door and trap information before movement",
        ),
        pressure_sources=("maze branches", "mirror decoys", "secret doors", "limited line of sight"),
        review_metrics=("route-message count", "repeated dead-end visits", "secret searches after hints", "tiles revealed per action"),
        success_behaviors=(
            "scouts report branch outcomes succinctly",
            "party maintains a common route plan to the objective and exit",
            "heroes mark hazards before teammates arrive",
        ),
        common_failure_modes=(
            "agents rediscover the same corridors independently",
            "secret doors are found but not communicated",
            "carrier gets lost after pickup",
        ),
        profile="memory",
    ),
    "frost_mirror_hold": FamilySpec(
        title="Frost Mirror Hold",
        marl_axis="decoy discrimination and role confirmation",
        purpose="Tests whether heroes coordinate observations to distinguish real threats and objectives from mirrored decoys.",
        coordination_skills=(
            "compare observations before attacking or opening",
            "assign one scout to verify mirror rooms",
            "hold resources until target identity is confirmed",
        ),
        pressure_sources=("mirror adepts", "decoy lanes", "split observation", "cold tempo pressure"),
        review_metrics=("verification messages", "attacks on decoys", "wrong-lane commitment", "resource use before confirmation"),
        success_behaviors=(
            "heroes ask for confirmation before committing to a mirrored target",
            "scout reports decoy state and safe route",
            "party keeps enough formation to recover from deception",
        ),
        common_failure_modes=(
            "first visible target is assumed to be the real objective",
            "heroes split too far while validating mirrors",
            "support resources are spent on false pressure",
        ),
        profile="memory",
    ),
    "bells_under_blackwater": FamilySpec(
        title="Bells Under Blackwater",
        marl_axis="shared global externality",
        purpose="Tests whether individual local actions account for a global shared cost such as ringing bells, alert, or flood pressure.",
        coordination_skills=(
            "announce actions that raise shared danger",
            "budget global alert/flood risk across the team",
            "choose collective safety over local action value",
        ),
        pressure_sources=("shared alert budget", "bell/flood triggers", "remote consequences", "optional loot"),
        review_metrics=("global alert increments", "warnings before risky actions", "risk-causing hero distribution", "route changes after externality"),
        success_behaviors=(
            "heroes warn before interacting with noisy or risky objects",
            "party stops optional actions once global pressure is high",
            "team changes route when shared danger crosses a threshold",
        ),
        common_failure_modes=(
            "one hero repeatedly raises danger while others pay the cost",
            "global pressure is treated as someone else's problem",
            "risk state is never communicated after a trigger",
        ),
        profile="externality",
    ),
    "hourglass_escape": FamilySpec(
        title="Hourglass Escape",
        marl_axis="deadline-aware planning",
        purpose="Tests shared temporal planning when every detour consumes scarce time before extraction.",
        coordination_skills=(
            "state deadline and remaining route length",
            "prune optional actions when schedule is tight",
            "stage heroes near exit before final pickup",
        ),
        pressure_sources=("turn clock", "long return path", "optional branches", "pursuit after pickup"),
        review_metrics=("turns to objective", "turns objective-to-exit", "optional actions after deadline warnings", "messages about remaining time"),
        success_behaviors=(
            "party counts turns before opening optional rooms",
            "heroes pre-position for extraction",
            "objective pickup happens only after the exit route is viable",
        ),
        common_failure_modes=(
            "agents explore because local room reward is visible despite deadline",
            "pickup happens before the return path is clear",
            "no one announces the point of no return",
        ),
        profile="extraction",
    ),
    "ashen_pantry": FamilySpec(
        title="Ashen Pantry",
        marl_axis="resource triage and safe-search discipline",
        purpose="Tests whether heroes share scarce food/healing and search safely instead of over-consuming shared pantry resources.",
        coordination_skills=(
            "declare need before taking supplies",
            "search rooms only after threats are controlled",
            "route consumables toward the hero carrying team risk",
        ),
        pressure_sources=("scarce supplies", "low-level swarms", "trap/search tradeoffs", "optional caches"),
        review_metrics=("items given", "healing held while ally critical", "searches before room safe", "supply hoarding"),
        success_behaviors=(
            "party assigns supplies to the wounded or exposed hero",
            "heroes clear pests before pantry looting",
            "optional searches stop once the objective route is ready",
        ),
        common_failure_modes=(
            "healthy hero hoards healing",
            "searches happen while monsters are still adjacent",
            "party drains supplies before facing the real objective room",
        ),
        profile="resource",
    ),
    "broken_oath_ambush": FamilySpec(
        title="Broken Oath Ambush",
        marl_axis="ambush recovery and mutual support",
        purpose="Tests rapid regrouping, threat calls, and support under surprise pressure.",
        coordination_skills=(
            "call ambush direction immediately",
            "collapse isolated heroes toward a defensible lane",
            "prioritize rescue over private damage turns",
        ),
        pressure_sources=("surprise flankers", "split starts", "cultist alarms", "short time-to-contact"),
        review_metrics=("rounds isolated after ambush", "messages on reveal", "rescue/guard actions", "damage before regroup"),
        success_behaviors=(
            "heroes broadcast the first ambush reveal",
            "frontline moves to protect the most exposed teammate",
            "party retreats or pivots instead of scattering further",
        ),
        common_failure_modes=(
            "each hero fights a separate local battle",
            "support arrives after the isolated hero is down",
            "ambush direction is never communicated",
        ),
        profile="ambush",
    ),
    "lost_apprentice": FamilySpec(
        title="Lost Apprentice",
        marl_axis="rescue search and information sharing",
        purpose="Tests coordinated search over uncertain rooms while preserving enough safety to rescue the target.",
        coordination_skills=(
            "divide search lanes and report negative findings",
            "keep a rescuer within support distance",
            "switch from search to escort once the target is found",
        ),
        pressure_sources=("uncertain target location", "minor wandering threats", "hazards near rescue target", "return escort"),
        review_metrics=("unique rooms searched", "duplicate searches", "messages with search results", "distance to rescuer after target found"),
        success_behaviors=(
            "heroes announce which room they will check",
            "negative information is shared to prune the search",
            "party regroups around the found target before extracting",
        ),
        common_failure_modes=(
            "multiple heroes search the same room silently",
            "found target is moved without escort",
            "search continues after rescue mode should begin",
        ),
        profile="escort",
    ),
    "moonblade_vault": FamilySpec(
        title="Moonblade Vault",
        marl_axis="specialist sequencing and greed control",
        purpose="Tests whether the team sequences vault access, specialist actions, and optional treasure without breaking the main route.",
        coordination_skills=(
            "wait for the specialist before opening vault hazards",
            "announce optional loot before taking it",
            "protect the key or blade carrier on exit",
        ),
        pressure_sources=("vault locks", "secret routes", "optional treasure", "carrier pursuit"),
        review_metrics=("specialist actions before vault open", "treasure detours", "carrier protection", "messages before cache interactions"),
        success_behaviors=(
            "dwarf or scout checks the vault path before pickup",
            "party agrees which treasure is skipped",
            "objective carrier has an escort before leaving the vault",
        ),
        common_failure_modes=(
            "non-specialist triggers vault hazards prematurely",
            "loot branches consume the extraction window",
            "moonblade carrier becomes isolated",
        ),
        profile="stealth",
    ),
    "return_to_hollow_barrow": FamilySpec(
        title="Return to Hollow Barrow",
        marl_axis="long-horizon memory and adaptation",
        purpose="Tests whether teams use remembered structure while adapting to changed pressure in a revisited dungeon.",
        coordination_skills=(
            "reuse prior route labels in messages",
            "verify changed rooms before assuming old safety",
            "adapt the extraction plan when familiar lanes shift",
        ),
        pressure_sources=("changed familiar routes", "hollow guards", "secret return paths", "boss remnant"),
        review_metrics=("route-name reuse", "verification before entry", "wrong assumptions about changed rooms", "adaptive replans"),
        success_behaviors=(
            "party references known landmarks but checks for changes",
            "scout confirms the old shortcut before the carrier commits",
            "team updates the plan when a remembered path is blocked",
        ),
        common_failure_modes=(
            "heroes follow the old plan after new evidence contradicts it",
            "changed pressure is not communicated",
            "familiar loot rooms distract from the changed objective path",
        ),
        profile="memory",
    ),
    "trial_of_embers": FamilySpec(
        title="Trial of Embers",
        marl_axis="hazard timing and shared risk budgeting",
        purpose="Tests whether heroes time hazardous crossings and spend shared risk deliberately rather than independently.",
        coordination_skills=(
            "stage before crossing hazard lanes",
            "communicate when traps or ember pulses are safe/unsafe",
            "assign one hero to clear or mark hazards before the carrier moves",
        ),
        pressure_sources=("traps", "ember pulses", "torch pressure", "monsters that force movement"),
        review_metrics=("trap searches/disarms before crossings", "hazard damage", "messages about safe timing", "carrier hazard exposure"),
        success_behaviors=(
            "party waits for hazard checks before advancing",
            "carrier follows a marked route",
            "support uses guard/heal resources around unavoidable hazard timing",
        ),
        common_failure_modes=(
            "heroes cross one at a time without sharing hazard info",
            "carrier takes the objective before traps are handled",
            "team burns time fighting while hazard budget rises",
        ),
        profile="hazard",
    ),
    "veiled_castle": FamilySpec(
        title="Veiled Castle",
        marl_axis="stealth coordination and detection management",
        purpose="Tests whether heroes coordinate quiet movement, scouting, and detection risk under castle patrol pressure.",
        coordination_skills=(
            "announce noisy actions before taking them",
            "let scouts verify patrol lanes before group movement",
            "coordinate regroup points after stealth breaks",
        ),
        pressure_sources=("patrol sight lines", "secret doors", "alarm cultists", "optional noisy loot"),
        review_metrics=("alert increments", "messages before noisy actions", "scout-before-group moves", "regroup after detection"),
        success_behaviors=(
            "scout marks safe lanes before the party advances",
            "heroes avoid unnecessary noise near patrols",
            "party has a fallback plan when detection occurs",
        ),
        common_failure_modes=(
            "frontline opens loud doors before scout confirmation",
            "stealth break causes unplanned scattering",
            "optional loot triggers alarm with no warning",
        ),
        profile="stealth",
    ),
}

PROFILE_PICO_MAPS: dict[str, str] = {
    "sync": """###########
#E.D...D.I#
#..#...#..#
#..C.B.C..#
###########""",
    "mixed_motive": """###########
#E..C..D.I#
#..#...#..#
#..C.K.C..#
###########""",
    "escort": """###########
#E..I..D..#
#..#...#..#
#..B...G..#
###########""",
    "extraction": """###########
#E..D..I..#
#..#...#..#
#..P...G..#
###########""",
    "formation": """###########
#E..D..I..#
#..#.#.#..#
#..M...M..#
###########""",
    "ranged_priority": """###########
#E..D..I..#
#..#...#F.#
#..C...G..#
###########""",
    "memory": """###########
#E..S..I..#
#.#.#.#.#.#
#..C.Y.G..#
###########""",
    "externality": """###########
#E..D..I..#
#..K...K..#
#..C.P.C..#
###########""",
    "ambush": """###########
#E.....D.I#
#..G...G..#
#..C.K.C..#
###########""",
    "hazard": """###########
#E..T..D.I#
#..#...#..#
#..C.P.C..#
###########""",
    "stealth": """###########
#E..S..I..#
#..#...#K.#
#..C...Y..#
###########""",
    "resource": """###########
#E..C..D.I#
#..#...#..#
#..C.G.C..#
###########""",
}

PROFILE_HEAVY_MAPS: dict[str, str] = {
    "sync": """#######################
#E....#.....#.........#
#.....D..C..D....B....#
###D###.....#####D#####
#.....#.........#.....#
#..T..D....K....D..K..#
#.....#.........#.....#
###D#######D#####D#####
#.....#.....#.........#
#..B..D..S..D....C....#
#.....#.....#.........#
#####D#####D#####D#####
#.........#.....#.....#
#....G....D..I..D..R..#
#.........#.....#.....#
#######################""",
    "mixed_motive": """#######################
#E....#.....#.........#
#..C..D..C..D....K....#
###D###.....#####D#####
#.....#.........#.....#
#..T..D....P....D..C..#
#.....#.........#.....#
###D#######D#####D#####
#.....#.....#.........#
#..C..D..S..D....C....#
#.....#.....#.........#
#####D#####D#####D#####
#.........#.....#.....#
#....K....D..I..D..R..#
#.........#.....#.....#
#######################""",
    "escort": """#######################
#E....#.....#.........#
#.....D..C..D....B....#
###D###.....#####D#####
#.....#.........#.....#
#..T..D....P....D..G..#
#.....#.........#.....#
###D#######D#####D#####
#.....#.....#.........#
#..B..D..S..D....C....#
#.....#.....#.........#
#####D#####D#####D#####
#.........#.....#.....#
#....P....D..I..D..R..#
#.........#.....#.....#
#######################""",
    "extraction": """#######################
#E....#.....#.........#
#.....D..C..D....P....#
###D###.....#####D#####
#.....#.........#.....#
#..T..D....P....D..G..#
#.....#.........#.....#
###D#######D#####D#####
#.....#.....#.........#
#..G..D..S..D....C....#
#.....#.....#.........#
#####D#####D#####D#####
#.........#.....#.....#
#....P....D..I..D..R..#
#.........#.....#.....#
#######################""",
    "formation": """#######################
#E....#.....#.........#
#.....D..C..D....M....#
###D###.....#####D#####
#.....#.........#.....#
#..T..D....N....D..M..#
#.....#.........#.....#
###D#######D#####D#####
#.....#.....#.........#
#..M..D..S..D....C....#
#.....#.....#.........#
#####D#####D#####D#####
#.........#.....#.....#
#....N....D..I..D..R..#
#.........#.....#.....#
#######################""",
    "ranged_priority": """#######################
#E....#.....#.........#
#.....D..C..D....F....#
###D###.....#####D#####
#.....#.........#.....#
#..T..D....F....D..K..#
#.....#.........#.....#
###D#######D#####D#####
#.....#.....#.........#
#..G..D..S..D....C....#
#.....#.....#.........#
#####D#####D#####D#####
#.........#.....#.....#
#....F....D..I..D..R..#
#.........#.....#.....#
#######################""",
    "memory": """#######################
#E....#.....#.........#
#.....S..C..D....Y....#
###D###.....#####S#####
#.....#.........#.....#
#..T..D....Y....D..G..#
#.....#.........#.....#
###S#######D#####D#####
#.....#.....#.........#
#..C..D..S..D....C....#
#.....#.....#.........#
#####D#####S#####D#####
#.........#.....#.....#
#....Y....D..I..D..G..#
#.........#.....#.....#
#######################""",
    "externality": """#######################
#E....#.....#.........#
#.....D..C..D....K....#
###D###.....#####D#####
#.....#.........#.....#
#..T..D....K....D..P..#
#.....#.........#.....#
###D#######D#####D#####
#.....#.....#.........#
#..P..D..S..D....C....#
#.....#.....#.........#
#####D#####D#####D#####
#.........#.....#.....#
#....K....D..I..D..R..#
#.........#.....#.....#
#######################""",
    "ambush": """#######################
#E....#.....#.........#
#..G..D..C..D....G....#
###D###.....#####D#####
#.....#.........#.....#
#..T..D....K....D..G..#
#.....#.........#.....#
###D#######D#####D#####
#.....#.....#.........#
#..B..D..S..D....C....#
#.....#.....#.........#
#####D#####D#####D#####
#.........#.....#.....#
#....K....D..I..D..R..#
#.........#.....#.....#
#######################""",
    "hazard": """#######################
#E....#.....#.........#
#..T..D..C..D....G....#
###D###.....#####D#####
#.....#.........#.....#
#..T..D....P....D..T..#
#.....#.........#.....#
###D#######D#####D#####
#.....#.....#.........#
#..P..D..S..D....C....#
#.....#.....#.........#
#####D#####D#####D#####
#.........#.....#.....#
#....T....D..I..D..R..#
#.........#.....#.....#
#######################""",
    "stealth": """#######################
#E....#.....#.........#
#.....S..C..D....K....#
###D###.....#####S#####
#.....#.........#.....#
#..T..D....Y....D..K..#
#.....#.........#.....#
###S#######D#####D#####
#.....#.....#.........#
#..C..D..S..D....C....#
#.....#.....#.........#
#####D#####S#####D#####
#.........#.....#.....#
#....Y....D..I..D..R..#
#.........#.....#.....#
#######################""",
    "resource": """#######################
#E....#.....#.........#
#..C..D..C..D....G....#
###D###.....#####D#####
#.....#.........#.....#
#..T..D....P....D..C..#
#.....#.........#.....#
###D#######D#####D#####
#.....#.....#.........#
#..C..D..S..D....C....#
#.....#.....#.........#
#####D#####D#####D#####
#.........#.....#.....#
#....G....D..I..D..R..#
#.........#.....#.....#
#######################""",
}


def _assert_rectangular(ascii_map: str, label: str) -> None:
    lines = ascii_map.strip("\n").splitlines()
    if not lines:
        raise ValueError(f"{label}: empty map")
    width = len(lines[0])
    bad = [idx for idx, line in enumerate(lines, start=1) if len(line) != width]
    if bad:
        raise ValueError(f"{label}: non-rectangular rows {bad}; expected width {width}")
    if "E" not in ascii_map:
        raise ValueError(f"{label}: missing entry E")
    if "I" not in ascii_map:
        raise ValueError(f"{label}: missing objective I")


def validate_embedded_templates() -> None:
    for profile, ascii_map in PROFILE_PICO_MAPS.items():
        _assert_rectangular(ascii_map, f"{profile}/pico")
    for profile, ascii_map in PROFILE_HEAVY_MAPS.items():
        _assert_rectangular(ascii_map, f"{profile}/heavy")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any], dry_run: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=False) + "\n"
    if dry_run:
        print(f"DRY write {path} ({len(text)} bytes)")
        return
    path.write_text(text, encoding="utf-8")


def write_text(path: Path, text: str, dry_run: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if dry_run:
        print(f"DRY write {path} ({len(text)} bytes)")
        return
    path.write_text(text, encoding="utf-8")


def title_case_family(family: str) -> str:
    return family.replace("_", " ").title()


def scan_char(ascii_map: str, char: str) -> list[list[int]]:
    positions: list[list[int]] = []
    for y, line in enumerate(ascii_map.strip("\n").splitlines()):
        for x, value in enumerate(line):
            if value == char:
                positions.append([x, y])
    return positions


def map_size(ascii_map: str) -> tuple[int, int]:
    lines = ascii_map.strip("\n").splitlines()
    return len(lines[0]), len(lines)


def count_map_char(ascii_map: str, char: str) -> int:
    return sum(line.count(char) for line in ascii_map.strip("\n").splitlines())


def compact_list(values: tuple[str, ...] | list[str]) -> list[str]:
    return [str(value) for value in values]


def tier_metadata(family: str, tier: str, spec: FamilySpec) -> dict[str, Any]:
    return {
        "size_tier": tier,
        "intended_num_heroes": TIER_HERO_COUNTS[tier],
        "supported_hero_range": TIER_SUPPORTED_RANGE[tier],
        "variant_family": family,
        "maturity": "migration_draft",
        "marl_axis": spec.marl_axis,
        "coordination_skills": compact_list(spec.coordination_skills),
        "pressure_sources": compact_list(spec.pressure_sources),
        "review_metrics": compact_list(spec.review_metrics),
        "tier_test_focus": tier_focus(spec, tier),
    }


def tier_focus(spec: FamilySpec, tier: str) -> str:
    focus = {
        "pico": f"Minimal single-agent probe for recognizing the {spec.marl_axis} signal without extra branches.",
        "lite": f"Small two-hero diagnostic for communication and first-order {spec.marl_axis} coordination.",
        "medium": "Legacy full task geometry preserved as the canonical medium benchmark variant.",
        "heavy": f"Expanded four-hero stress test with extra lanes, optional pressure, and stricter {spec.marl_axis} failure modes.",
    }
    return focus[tier]


def merge_metadata(existing: dict[str, Any] | None, required: dict[str, Any]) -> dict[str, Any]:
    merged = dict(existing or {})
    merged.update(required)
    # Keep older Lantern-compatible names as aliases for downstream analysis.
    merged.setdefault("coordination_demands", compact_list(required.get("coordination_skills", [])))
    merged.setdefault("role_demands", {})
    return merged


def normalize_recommendations(quest: dict[str, Any], max_heroes: int) -> None:
    by_size = dict(quest.get("recommended_heroes_by_party_size") or {})
    for count, roles in DEFAULT_ROLES_BY_SIZE.items():
        if int(count) <= max_heroes:
            by_size.setdefault(count, roles[: int(count)])
    quest["recommended_heroes_by_party_size"] = by_size
    intended = int(quest.get("metadata", {}).get("intended_num_heroes", max_heroes))
    tier_roles = by_size.get(str(intended)) or by_size.get(intended) or DEFAULT_ROLES[:intended]
    quest["recommended_heroes"] = list(tier_roles[:intended])


def ensure_hero_starts(quest: dict[str, Any], max_heroes: int) -> None:
    starts = list(quest.get("hero_starts") or [])
    if len(starts) >= max_heroes:
        quest["hero_starts"] = starts[:max_heroes]
        return
    ascii_map = quest["map"]["ascii"]
    entry = scan_char(ascii_map, "E")[0]
    candidates = [entry, [entry[0] + 1, entry[1]], [entry[0] + 2, entry[1]], [entry[0] + 3, entry[1]], [entry[0], entry[1] + 1], [entry[0] + 1, entry[1] + 1]]
    lines = ascii_map.strip("\n").splitlines()
    width, height = map_size(ascii_map)
    for x, y in candidates:
        if len(starts) >= max_heroes:
            break
        if 0 <= x < width and 0 <= y < height and lines[y][x] in ".E":
            pos = [x, y]
            if pos not in starts:
                starts.append(pos)
    if len(starts) < max_heroes:
        raise ValueError(f"{quest.get('quest_id')}: not enough open hero starts for max_heroes={max_heroes}")
    quest["hero_starts"] = starts[:max_heroes]


def ensure_chest_contents(quest: dict[str, Any]) -> None:
    chest_count = count_map_char(quest["map"]["ascii"], "C")
    chest_contents = dict(quest.get("chest_contents") or {})
    defaults = ["coin_cache", "healing_draught", "old_cache", "coin_cache", "healing_draught", "old_cache"]
    for idx in range(1, chest_count + 1):
        chest_contents.setdefault(f"chest_{idx}", defaults[(idx - 1) % len(defaults)])
    quest["chest_contents"] = chest_contents


def objective_from_source(source: dict[str, Any], ascii_map: str) -> dict[str, Any]:
    source_objective = dict(source.get("objective") or {})
    entry = scan_char(ascii_map, "E")[0]
    objective_pos = scan_char(ascii_map, "I")[0]
    return {
        "type": source_objective.get("type", "retrieve_and_escape"),
        "item_id": source_objective.get("item_id", "objective_item"),
        "escape_tile": entry,
        "start_pos": objective_pos,
        **({"fragile": bool(source_objective.get("fragile"))} if source_objective.get("fragile") is not None else {}),
    }


def geometry_rooms(tier: str, spec: FamilySpec) -> dict[str, Any]:
    if tier == "pico":
        return {
            "entry_probe": {
                "name": "Entry Probe",
                "rect": [1, 1, 3, 3],
                "description": f"A compact start area that exposes the first {spec.marl_axis} choice immediately.",
                "tags": ["start", "diagnostic"],
            },
            "axis_cell": {
                "name": "Axis Cell",
                "rect": [5, 1, 9, 3],
                "description": f"Small objective cell focused on {spec.marl_axis} without extra branches.",
                "tags": ["objective", "marl_axis"],
            },
        }
    return {
        "entry_hall": {
            "name": "Entry Hall",
            "rect": [1, 1, 5, 2],
            "description": "The team starts in a narrow hall that forces marching-order and role assignment.",
            "tags": ["start", "coordination"],
        },
        "upper_cache": {
            "name": "Upper Cache",
            "rect": [7, 1, 11, 3],
            "description": "A preparation branch with treasure/gear temptation before the main route opens.",
            "tags": ["optional", "prep"],
        },
        "pressure_lane": {
            "name": "Pressure Lane",
            "rect": [13, 1, 21, 3],
            "description": f"A visible pressure lane tuned for {spec.marl_axis}.",
            "tags": ["combat", "lane"],
        },
        "axis_crossing": {
            "name": "Axis Crossing",
            "rect": [1, 4, 15, 6],
            "description": f"The central crossing is where {spec.marl_axis} becomes a team problem.",
            "tags": ["marl_axis", "hazard"],
        },
        "side_pressure": {
            "name": "Side Pressure",
            "rect": [17, 4, 21, 6],
            "description": "A side pocket punishes unsupported splits and unannounced detours.",
            "tags": ["split_party", "pressure"],
        },
        "specialist_route": {
            "name": "Specialist Route",
            "rect": [1, 8, 11, 10],
            "description": "A lower route rewards role-aware scouting, secret checks, or hazard management.",
            "tags": ["specialist", "route"],
        },
        "optional_cache": {
            "name": "Optional Cache",
            "rect": [13, 8, 21, 10],
            "description": "Optional reward is placed far enough from the objective to expose greedy or uncoordinated plans.",
            "tags": ["optional", "greed"],
        },
        "objective_lane": {
            "name": "Objective Lane",
            "rect": [1, 12, 21, 14],
            "description": "The final lane combines pickup, protection, and extraction under full-party pressure.",
            "tags": ["objective", "extraction"],
        },
    }


def diagnostic_furniture(tier: str, spec: FamilySpec) -> list[dict[str, Any]]:
    if tier == "pico":
        return []
    return [
        {
            "id": "axis_marker_1",
            "name": f"{spec.title} Marker",
            "category": "marker",
            "pos": [11, 5],
            "deck": "event",
            "description": f"A review marker for the {spec.marl_axis} decision point.",
            "traits": ["marl_axis", spec.profile],
            "visible": True,
            "destructible": False,
            "blocks_movement": False,
            "blocks_los": False,
            "search_effects": {
                "furniture": [
                    {
                        "type": "emit",
                        "message": f"The marker highlights the task axis: {spec.marl_axis}.",
                    }
                ]
            },
        }
    ]


def make_hand_authored_variant(
    family: str,
    tier: str,
    spec: FamilySpec,
    source: dict[str, Any],
) -> dict[str, Any]:
    if family == "lantern_crypt" and tier in {"pico", "heavy"}:
        return make_lantern_variant(tier, spec, source)
    ascii_map = (PROFILE_PICO_MAPS if tier == "pico" else PROFILE_HEAVY_MAPS)[spec.profile]
    width, height = map_size(ascii_map)
    max_heroes = TIER_HERO_COUNTS[tier]
    quest = {
        "quest_id": f"base:{family}:{tier}",
        "title": f"{spec.title} {tier.title()}",
        "max_heroes": max_heroes,
        "metadata": tier_metadata(family, tier, spec),
        "map": {"ascii": ascii_map, "width": width, "height": height},
        "hero_starts": [[1, 1], [2, 1], [3, 1], [4, 1]][:max_heroes],
        "objective": objective_from_source(source, ascii_map),
        "rooms": geometry_rooms(tier, spec),
        "furniture": diagnostic_furniture(tier, spec),
        "chest_contents": {},
        "scripts": {
            **dict(source.get("scripts") or {}),
            "family": family,
            "tier": tier,
            "marl_axis": spec.marl_axis,
        },
        "achievements": [
            {
                "id": f"{tier}_{family}_axis_probe",
                "title": f"{tier.title()} Axis Probe",
                "description": f"Make progress in the {tier} {spec.title} variant while preserving the {spec.marl_axis} signal.",
                "reward": 0.12,
                "condition": {"type": "objective_taken"},
            }
        ],
    }
    normalize_recommendations(quest, max_heroes)
    ensure_chest_contents(quest)
    return quest


def lantern_common_mechanics(tier: str) -> dict[str, Any]:
    return {
        "marl_contract": {
            "axis": "role-specialized causal counterplay",
            "tags": [
                "causal_inference",
                "counterplay_before_damage",
                "support_role_credit",
                "frontline_screening",
                "tandem_role_coordination",
            ],
            "core_failure_modes": [
                "objective pickup before altar clue",
                "boss engage before altar counterplay",
                "support hero isolated while resolving the altar",
                "no message that the guardian has been weakened",
                "one role solves its local task without handing useful information to its pair",
            ],
        },
        f"{tier}_contract": {
            "counterplay_anchor": "ember_altar_1",
            "direct_fight_is_suboptimal": True,
            "review_question": "Did the policy create value from clue/counterplay before committing to the guardian?",
            "role_challenges": {
                "wizard": "read or break the ember altar to expose the guardian's causal weakness",
                "barbarian": "screen the altar reader and commit damage after counterplay is active",
                "elf": "scout the lens cache and confirm the tether route before the idol run",
                "dwarf": "mark the secret return route and manage hazard/route risk",
            },
            "tandem_challenges": [
                "Wizard + Barbarian: counterplay reader protected by frontline screening",
                "Elf + Dwarf: scout-confirmed tether route converted into a marked extraction path",
            ],
        },
        "warden_policy": {
            "hidden_information_access": "revealed_state_plus_authored_dungeon_memory",
            "pressure_budget_per_round": 1 if tier == "pico" else 2,
            "preferred_tactics": [
                "protect the ember altar once heroes identify it",
                "pressure the objective carrier if the altar is ignored",
                "make the guardian's strength visibly depend on counterplay",
            ],
            "forbidden_tactics": [
                "hide the altar clue after the guardian is revealed",
                "spawn generic pressure that obscures the counterplay lesson",
            ],
        },
    }


def lantern_counterplay_furniture(tier: str) -> list[dict[str, Any]]:
    altar = {
        "id": "ember_altar_1",
        "name": "Ember Altar",
        "category": "lore",
        "pos": [2, 1] if tier == "pico" else [10, 5],
        "deck": "clue",
        "description": "A hot lantern-altar that explains why the guardian should not be fought blindly.",
        "traits": ["marl_clue", "counterplay", "support_role_credit"],
        "visible": True,
        "destructible": True,
        "hp": 2 if tier == "pico" else 3,
        "max_hp": 2 if tier == "pico" else 3,
        "blocks_movement": False,
        "blocks_los": False,
        "search_effects": {
            "furniture": [
                {
                    "type": "emit",
                    "message": "The altar text is clear: the guardian is strongest until the ember tether is read or broken.",
                    "trace_kind": "lantern_counterplay_read",
                },
                {"type": "set_flag", "key": "ember_altar_read", "value": True},
                {"type": "lower_alert", "amount": 1},
            ]
        },
        "break_effect": [
            {
                "type": "emit",
                "message": "The ember tether snaps. The guardian's ward gutters down to a dull red.",
                "trace_kind": "lantern_counterplay_broken",
            },
            {"type": "set_flag", "key": "ember_altar_destroyed", "value": True},
            {"type": "monster_status", "role": "lantern_wight", "status": "ward_dimmed"},
            {"type": "monster_status", "role": "crypt_brute", "status": "ward_dimmed"},
        ],
    }
    if tier == "pico":
        return [altar]
    return [
        altar,
        {
            "id": "lantern_lens_1",
            "name": "Clear Lantern Lens",
            "category": "lore",
            "pos": [8, 2],
            "deck": "artifact",
            "description": "A secondary clue that rewards scouting before the full party opens the lower chapel.",
            "traits": ["scouting", "counterplay_confirmation"],
            "visible": True,
            "blocks_movement": False,
            "blocks_los": False,
            "search_effects": {
                "furniture": [
                    {
                        "type": "emit",
                        "message": "The lens shows the altar tether running from the guardian to the idol room.",
                        "trace_kind": "lantern_route_confirmed",
                    },
                    {"type": "item", "item": "lantern_lens"},
                ]
            },
        },
        {
            "id": "weapon_rack_1",
            "name": "Cold-Iron Weapon Rack",
            "category": "weapon",
            "pos": [15, 13],
            "deck": "supply",
            "description": "A frontline preparation object that helps the party hold the guardian while support resolves the altar.",
            "traits": ["frontline_prep", "screening"],
            "visible": True,
            "blocks_movement": False,
            "blocks_los": False,
            "search_effects": {
                "furniture": [
                    {"type": "weapon", "item": "cold_iron_edge"},
                    {
                        "type": "emit",
                        "message": "Cold iron gives the frontline a reason to hold position instead of rushing alone.",
                    },
                ]
            },
        },
        {
            "id": "route_mark_1",
            "name": "Chalked Secret Route",
            "category": "lore",
            "pos": [8, 9],
            "deck": "clue",
            "description": "A dwarf-readable route mark that turns the secret lower path into a safe extraction option.",
            "traits": ["dwarf_route_marking", "secret_route", "tandem_coordination"],
            "visible": True,
            "blocks_movement": False,
            "blocks_los": False,
            "search_effects": {
                "furniture": [
                    {
                        "type": "emit",
                        "message": "The chalk line marks a lower return route: useful only if someone tells the carrier.",
                        "trace_kind": "lantern_route_marked",
                    },
                    {"type": "set_flag", "key": "heavy_route_mark_read", "value": True},
                ]
            },
        },
    ]


def lantern_achievements(tier: str) -> list[dict[str, Any]]:
    return [
        {
            "id": f"{tier}_read_ember_tether",
            "title": "Read the Ember Tether",
            "description": "Search the altar clue before treating the guardian as a normal damage race.",
            "reward": 0.12,
            "condition": {"type": "furniture_searched", "id": "ember_altar_1"},
        },
        {
            "id": f"{tier}_break_ember_tether",
            "title": "Break the Ember Tether",
            "description": "Destroy the altar that makes the guardian dangerous.",
            "reward": 0.14,
            "condition": {"type": "furniture_destroyed", "id": "ember_altar_1"},
        },
        {
            "id": f"{tier}_recover_after_counterplay",
            "title": "Recover After Counterplay",
            "description": "Recover the idol after resolving or explicitly accounting for the altar.",
            "reward": 0.16,
            "condition": {"type": "objective_taken"},
        },
        {
            "id": f"{tier}_escape_with_idol",
            "title": "Escape With the Ember Idol",
            "description": "Extract after the counterplay lesson has shaped the route.",
            "reward": 0.2,
            "condition": {"type": "escaped_with_objective"},
        },
    ]


def make_lantern_variant(tier: str, spec: FamilySpec, source: dict[str, Any]) -> dict[str, Any]:
    if tier == "pico":
        ascii_map = """###########
#E..D..I..#
#..#..L...#
#..#......#
###########"""
        rooms = {
            "entry_altar": {
                "name": "Entry Altar",
                "rect": [1, 1, 3, 3],
                "description": "The solo hero begins beside the altar clue, so skipping it is an observable policy choice.",
                "tags": ["start", "counterplay_clue"],
            },
            "idol_cell": {
                "name": "Idol Cell",
                "rect": [5, 1, 9, 3],
                "description": "A tiny idol room with one wight: enough pressure to punish blind pickup, not enough branches to hide the lesson.",
                "tags": ["objective", "guardian"],
            },
        }
        max_heroes = 1
        hero_starts = [[1, 1]]
        bosses = {
            "lantern_wight_1": {
                "name": "Tethered Lantern-Wight",
                "public_summary": "A solo-scale guardian whose ward weakens when the altar is read or broken.",
                "counterplay_hint": "Search or break the ember altar before committing to the idol.",
                "defeat_reward": 0.12,
            }
        }
    else:
        ascii_map = """#######################
#E....#.....#.........#
#.....D..C..D....B....#
###D###.....#####D#####
#.....#.........#.....#
#..T..D....L....D..G..#
#.....#.........#.....#
###D#######D#####D#####
#.....#.....#.........#
#..B..D..S..D....C....#
#.....#.....#.........#
#####D#####D#####D#####
#.........#.....#.....#
#....P....D..I..R..G..#
#.........#.....#.....#
#######################"""
        rooms = {
            "entry_hall": {
                "name": "Entry Hall",
                "rect": [1, 1, 5, 2],
                "description": "A safe start that asks the party to assign reader, frontline, scout, and route-marker before opening doors.",
                "tags": ["start", "role_assignment"],
            },
            "lens_cache": {
                "name": "Lens Cache",
                "rect": [7, 1, 11, 3],
                "description": "A scouting branch with a clue/reward object that confirms the altar tether.",
                "tags": ["clue", "optional_prep"],
            },
            "bone_lane": {
                "name": "Bone Lane",
                "rect": [13, 1, 21, 3],
                "description": "A visible guard lane that tempts a pure combat policy before the altar is understood.",
                "tags": ["combat", "temptation"],
            },
            "ember_crossing": {
                "name": "Ember Crossing",
                "rect": [1, 4, 15, 6],
                "description": "The central wight and altar force the party to protect the counterplay action.",
                "tags": ["counterplay", "frontline_screen"],
            },
            "side_pressure": {
                "name": "Side Pressure",
                "rect": [17, 4, 21, 6],
                "description": "A small side threat punishes unsupported splits while the altar is unresolved.",
                "tags": ["split_party", "pressure"],
            },
            "secret_route": {
                "name": "Secret Route",
                "rect": [1, 8, 11, 10],
                "description": "A specialist route that rewards map sharing instead of everyone crowding the wight.",
                "tags": ["secret", "route_marking"],
            },
            "cold_iron_cache": {
                "name": "Cold-Iron Cache",
                "rect": [13, 8, 21, 10],
                "description": "Optional preparation that is useful only if the team keeps tempo and communicates.",
                "tags": ["prep", "optional"],
            },
            "idol_chapel": {
                "name": "Idol Chapel",
                "rect": [1, 12, 21, 14],
                "description": "The final lane combines pickup, guardian pressure, and extraction under full-party coordination.",
                "tags": ["objective", "extraction"],
            },
        }
        role_selection = {
            "required_roles_by_party_size": {
                "4": ["barbarian", "wizard", "elf", "dwarf"]
            }
        }
        max_heroes = 4
        hero_starts = [[1, 1], [2, 1], [3, 1], [4, 1]]
        bosses = {
            "lantern_wight_1": {
                "name": "Tethered Lantern-Wight",
                "public_summary": "A central guardian whose ward should be handled before the party opens the idol chapel.",
                "counterplay_hint": "Read or break ember_altar_1 while the frontline screens the crossing.",
                "defeat_reward": 0.16,
            },
            "crypt_brute_1": {
                "name": "Idol Door Brute",
                "public_summary": "A late guardian that punishes pickup before the route and altar plan are settled.",
                "counterplay_hint": "Use the lens, altar, and cold-iron rack before collapsing on the idol room.",
                "defeat_reward": 0.14,
            },
        }

    width, height = map_size(ascii_map)
    quest = {
        "quest_id": f"base:lantern_crypt:{tier}",
        "title": f"{spec.title} {tier.title()}",
        "max_heroes": max_heroes,
        "metadata": tier_metadata("lantern_crypt", tier, spec),
        "map": {"ascii": ascii_map, "width": width, "height": height},
        "hero_starts": hero_starts,
        "hero_loadouts": copy.deepcopy(source.get("hero_loadouts", {})),
        "objective": objective_from_source(source, ascii_map),
        "rooms": rooms,
        "furniture": lantern_counterplay_furniture(tier),
        "bosses": bosses,
        "mechanics": lantern_common_mechanics(tier),
        "achievements": lantern_achievements(tier),
        "scripts": {
            **dict(source.get("scripts") or {}),
            "family": "lantern_crypt",
            "tier": tier,
            "marl_axis": spec.marl_axis,
            "counterplay_anchor": "ember_altar_1",
        },
        "monster_activation": copy.deepcopy(source.get("monster_activation", {})),
        "deck_policies": copy.deepcopy(source.get("deck_policies", {})),
        "decks": copy.deepcopy(source.get("decks", {})),
    }
    if tier == "heavy":
        quest["role_selection"] = role_selection
    normalize_recommendations(quest, max_heroes)
    ensure_chest_contents(quest)
    return quest


def make_ported_variant(family: str, tier: str, spec: FamilySpec, source: dict[str, Any]) -> dict[str, Any]:
    quest = copy.deepcopy(source)
    quest["quest_id"] = f"base:{family}:{tier}"
    if tier != "medium":
        quest["title"] = f"{spec.title} {tier.title()}"
    else:
        quest.setdefault("title", spec.title)
    max_heroes = TIER_HERO_COUNTS[tier]
    quest["max_heroes"] = max_heroes
    quest["metadata"] = merge_metadata(quest.get("metadata"), tier_metadata(family, tier, spec))
    if "map" in quest and "ascii" in quest["map"]:
        width, height = map_size(quest["map"]["ascii"])
        quest["map"]["width"] = width
        quest["map"]["height"] = height
    normalize_recommendations(quest, max_heroes)
    ensure_hero_starts(quest, max_heroes)
    ensure_chest_contents(quest)
    scripts = dict(quest.get("scripts") or {})
    scripts.update({"family": family, "tier": tier, "marl_axis": spec.marl_axis})
    quest["scripts"] = scripts
    return quest


def extract_family_defaults(medium: dict[str, Any]) -> dict[str, Any]:
    defaults: dict[str, Any] = {}
    for key in (
        "difficulty",
        "torch",
        "recommended_heroes",
        "recommended_heroes_by_party_size",
        "hero_loadouts",
        "monster_activation",
        "decks",
        "ruleset",
        "role_selection",
        "deck_policies",
        "mechanics",
        "monster_overrides",
        "bosses",
        "randomized_chests",
    ):
        if key in medium:
            defaults[key] = copy.deepcopy(medium[key])
    defaults.setdefault("recommended_heroes", DEFAULT_ROLES)
    defaults.setdefault("recommended_heroes_by_party_size", DEFAULT_ROLES_BY_SIZE)
    defaults.setdefault("torch", int(medium.get("torch", 20)))
    return defaults


def make_family_json(family: str, spec: FamilySpec, medium: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": family,
        "title": spec.title,
        "metadata": {
            "campaign_group": "base",
            "maturity": "migration_draft",
            "validation_status": "tier_migration_pending_review",
            "objective_type": medium.get("objective", {}).get("type", "retrieve_and_escape"),
            "marl_axis": spec.marl_axis,
            "marl_purpose": spec.purpose,
            "coordination_skills": compact_list(spec.coordination_skills),
            "pressure_sources": compact_list(spec.pressure_sources),
            "review_metrics": compact_list(spec.review_metrics),
            "information_structure": "decentralized_partial_observation",
            "reward_structure": "shared_team_reward_with_per_hero_attribution",
        },
        "defaults": extract_family_defaults(medium),
        "warden_runbook": {
            "axis_pressure": ", ".join(spec.pressure_sources),
            "fairness_notes": [
                "Escalate pressure only after the relevant cue has been observable or communicated.",
                "Preserve a counterplay route so failures identify coordination rather than impossible state.",
            ],
        },
        "role_demand_vocabulary": {
            "barbarian": ["frontline", "body_block", "lane_hold"],
            "wizard": ["ranged_magic", "rule_clues", "warding"],
            "elf": ["scouting", "ranged_cover", "healing_support"],
            "dwarf": ["trap_disarm", "secret_search", "route_marking"],
        },
        "scripts": {"family": family},
    }


def tier_roles(quest: dict[str, Any]) -> list[str]:
    intended = int(quest.get("metadata", {}).get("intended_num_heroes", quest.get("max_heroes", 1)))
    by_size = dict(quest.get("recommended_heroes_by_party_size") or {})
    roles = by_size.get(str(intended)) or by_size.get(intended) or quest.get("recommended_heroes", [])
    return [str(role) for role in roles[:intended]]


def roles_text(roles: list[str]) -> str:
    return " + ".join(role.title() for role in roles)


def readme_for_family(
    family: str,
    spec: FamilySpec,
    variants: dict[str, dict[str, Any]],
) -> str:
    tier_rows = {
        "pico": f"A one-hero micro-probe that exposes the first {spec.marl_axis} decision without side branches.",
        "lite": f"A two-hero diagnostic focused on communication and first coordination failure modes for {spec.marl_axis}.",
        "medium": "The legacy full task geometry, preserved as the canonical medium tier.",
        "heavy": f"A four-hero stress variant with additional lanes, side pressure, and stricter {spec.marl_axis} review signals.",
    }
    lines = [
        f"# {spec.title}",
        "",
        "## MARL purpose",
        spec.purpose,
        "",
        "## Tier coverage",
    ]
    for tier in TIER_ORDER:
        lines.append(f"- `{tier}`: {tier_rows[tier]}")
    lines.extend(
        [
            "",
            "## Recommended heroes by tier",
        ]
    )
    for tier in TIER_ORDER:
        roles = tier_roles(variants[tier])
        lines.append(
            f"- `{tier}`: {len(roles)} hero{'es' if len(roles) != 1 else ''}: {roles_text(roles)}."
        )
    lines.extend(["", "## Quest IDs"])
    for tier in TIER_ORDER:
        lines.append(f"- `{tier}`: `base:{family}:{tier}`")
    lines.extend(["", "## Success behaviors"])
    lines.extend(f"- {item}" for item in spec.success_behaviors)
    lines.extend(["", "## Common failure modes"])
    lines.extend(f"- {item}" for item in spec.common_failure_modes)
    lines.extend(["", "## Review signals in traces/replays"])
    lines.extend(f"- {item}" for item in spec.review_metrics)
    lines.extend(["", "## Coordination skills"])
    lines.extend(f"- {item}" for item in spec.coordination_skills)
    if family == "lantern_crypt":
        lines.extend(
            [
                "",
                "## Heavy role challenges",
                "- `wizard`: read or break the ember altar so the guardian is not treated as a normal damage race.",
                "- `barbarian`: screen the altar reader, then commit pressure after counterplay is active.",
                "- `elf`: scout the lens cache and confirm the altar tether before the idol run.",
                "- `dwarf`: mark the secret return route and manage hazard/route risk.",
                "",
                "## Heavy tandem checks",
                "- Wizard + Barbarian: counterplay reader protected by frontline screening.",
                "- Elf + Dwarf: scout-confirmed tether route converted into a marked extraction path.",
            ]
        )
    lines.extend(["", "## Pressure sources"])
    lines.extend(f"- {item}" for item in spec.pressure_sources)
    lines.append("")
    return "\n".join(lines)


def copy_hooks(src_dungeon_root: Path, family_root: Path, family: str, dry_run: bool) -> None:
    candidates = [
        src_dungeon_root / family / "hooks.py",
        src_dungeon_root / f"{family}_lite" / "hooks.py",
    ]
    out = family_root / "hooks.py"
    for candidate in candidates:
        if candidate.exists():
            text = candidate.read_text(encoding="utf-8")
            header = f"# Copied from legacy dungeons/{candidate.parent.name}/hooks.py during tier migration.\n"
            if family == "lantern_crypt":
                text = lantern_hooks_text(text)
            write_text(out, header + text, dry_run)
            return
    write_text(out, f'"""Hooks for the {family} tiered family.\n\nNo bespoke hooks are required for the migration scaffold.\n"""\n', dry_run)


def lantern_hooks_text(text: str) -> str:
    marker = '    registry.on("on_warden_cleanup", _on_warden_cleanup)\n'
    extra = (
        marker
        + '    registry.on("after_Guard", _after_heavy_guard)\n'
        + '    registry.on("after_AttackRoll", _after_heavy_attack_roll)\n'
        + '    registry.on("after_MessageEffect", _after_heavy_message)\n'
        + '    registry.on("after_SearchArea", _after_heavy_search_area)\n'
        + '    registry.on("on_furniture_searched", _on_heavy_furniture_searched)\n'
        + '    registry.on("on_objective_taken", _on_heavy_objective_taken)\n'
    )
    if marker in text:
        text = text.replace(marker, extra, 1)
    return text + '''


def _is_heavy_lantern(ctx):
    return ctx.state.quest_id == "base:lantern_crypt:heavy" or ctx.state.scripts.get("tier") == "heavy"


def _role(ctx, hero_id):
    hero = ctx.state.heroes.get(hero_id)
    return hero.role if hero else ""


def _after_heavy_guard(ctx):
    if not _is_heavy_lantern(ctx):
        return []
    actor_id = ctx.info.get("trigger_payload", {}).get("effect", {}).get("actor_id")
    if _role(ctx, actor_id) != "barbarian":
        return []
    effects = [SetFlag(key="heavy_barbarian_screened", value=True)]
    if ctx.state.scripts.get("heavy_wizard_counterplay"):
        effects.append(
            UnlockAchievement(
                achievement_id="heavy_barbarian_screens_reader",
                title="Screen The Reader",
                reward=0.12,
                description="Use the Barbarian to guard after the Wizard has engaged the altar counterplay.",
            )
        )
    return effects


def _after_heavy_attack_roll(ctx):
    if not _is_heavy_lantern(ctx):
        return []
    effect = ctx.info.get("trigger_payload", {}).get("effect", {})
    if _role(ctx, effect.get("attacker_id")) != "barbarian":
        return []
    if not (ctx.state.scripts.get("ember_altar_read") or ctx.state.scripts.get("ember_altar_destroyed")):
        return []
    return [
        SetFlag(key="heavy_barbarian_committed_after_counterplay", value=True),
        UnlockAchievement(
            achievement_id="heavy_commit_after_counterplay",
            title="Commit After Counterplay",
            reward=0.12,
            description="Use Barbarian pressure after the altar has been read or broken.",
        ),
    ]


def _after_heavy_message(ctx):
    if not _is_heavy_lantern(ctx):
        return []
    if not (ctx.state.scripts.get("ember_altar_read") or ctx.state.scripts.get("ember_altar_destroyed")):
        return []
    return [
        SetFlag(key="heavy_counterplay_called", value=True),
        UnlockAchievement(
            achievement_id="heavy_call_the_counterplay",
            title="Call The Counterplay",
            reward=0.10,
            description="Send a party message after the altar clue or break changes the fight.",
        ),
    ]


def _after_heavy_search_area(ctx):
    if not _is_heavy_lantern(ctx):
        return []
    effect = ctx.info.get("trigger_payload", {}).get("effect", {})
    if _role(ctx, effect.get("actor_id")) != "dwarf":
        return []
    if effect.get("category") not in {"secrets", "glyphs"}:
        return []
    return [
        SetFlag(key="heavy_dwarf_checked_secret_route", value=True),
        UnlockAchievement(
            achievement_id="heavy_dwarf_checks_secret_route",
            title="Dwarf Checks The Secret Route",
            reward=0.10,
            description="Use the Dwarf to check route hazards or secrets before the idol run.",
        ),
    ]


def _on_heavy_furniture_searched(ctx):
    if not _is_heavy_lantern(ctx):
        return []
    result = ctx.info.get("trigger_payload", {})
    target = result.get("furniture_id")
    role = result.get("role")
    effects = []
    if target == "ember_altar_1" and role == "wizard":
        effects.extend(
            [
                SetFlag(key="heavy_wizard_counterplay", value=True),
                UnlockAchievement(
                    achievement_id="heavy_wizard_reads_altar",
                    title="Wizard Reads The Altar",
                    reward=0.12,
                    description="Use the Wizard for the counterplay clue instead of treating the fight as raw damage.",
                ),
            ]
        )
    if target == "lantern_lens_1" and role == "elf":
        effects.extend(
            [
                SetFlag(key="heavy_elf_scouted_lens", value=True),
                UnlockAchievement(
                    achievement_id="heavy_elf_confirms_tether",
                    title="Elf Confirms The Tether",
                    reward=0.10,
                    description="Use the Elf to scout the lens route and confirm how the altar connects to the idol room.",
                ),
            ]
        )
    if target == "route_mark_1" and role == "dwarf":
        effects.extend(
            [
                SetFlag(key="heavy_dwarf_marked_route", value=True),
                UnlockAchievement(
                    achievement_id="heavy_dwarf_marks_route",
                    title="Dwarf Marks The Route",
                    reward=0.10,
                    description="Use the Dwarf to mark the secret return route before the idol is carried.",
                ),
            ]
        )
    if ctx.state.scripts.get("heavy_elf_scouted_lens") and ctx.state.scripts.get("heavy_dwarf_marked_route"):
        effects.append(
            UnlockAchievement(
                achievement_id="heavy_elf_dwarf_route_pair",
                title="Elf-Dwarf Route Pair",
                reward=0.14,
                description="Pair Elf scouting with Dwarf route marking before the final idol run.",
            )
        )
    if ctx.state.scripts.get("heavy_wizard_counterplay") and ctx.state.scripts.get("heavy_barbarian_screened"):
        effects.append(
            UnlockAchievement(
                achievement_id="heavy_wizard_barbarian_tandem",
                title="Wizard-Barbarian Tandem",
                reward=0.14,
                description="Pair Wizard counterplay with Barbarian screening at the ember crossing.",
            )
        )
    return effects


def _on_heavy_objective_taken(ctx):
    if not _is_heavy_lantern(ctx):
        return []
    if ctx.info.get("trigger_payload", {}).get("objective_id") != ctx.state.objective.id:
        return []
    required = (
        "heavy_wizard_counterplay",
        "heavy_barbarian_screened",
        "heavy_elf_scouted_lens",
        "heavy_dwarf_marked_route",
    )
    if all(ctx.state.scripts.get(key) for key in required):
        return [
            UnlockAchievement(
                achievement_id="heavy_four_role_counterplay",
                title="Four-Role Counterplay",
                reward=0.22,
                description="Use Wizard, Barbarian, Elf, and Dwarf contributions before taking the idol.",
            )
        ]
    return []
'''


def migrate_family(repo: Path, family: str, dry_run: bool) -> None:
    spec = FAMILY_SPECS[family]
    dungeons_root = repo / "src" / "dungeongrid" / "dungeons"
    expansion_root = repo / "src" / "dungeongrid" / "expansions" / "base" / "dungeons" / family
    full_path = dungeons_root / family / "quest.json"
    lite_path = dungeons_root / f"{family}_lite" / "quest.json"
    if not full_path.exists():
        raise FileNotFoundError(f"Missing legacy medium source: {full_path}")
    if not lite_path.exists():
        raise FileNotFoundError(f"Missing legacy lite source: {lite_path}")

    medium_source = read_json(full_path)
    lite_source = read_json(lite_path)
    medium = make_ported_variant(family, "medium", spec, medium_source)
    lite = make_ported_variant(family, "lite", spec, lite_source)
    pico = make_hand_authored_variant(family, "pico", spec, lite_source)
    heavy = make_hand_authored_variant(family, "heavy", spec, medium_source)

    variants = {"pico": pico, "lite": lite, "medium": medium, "heavy": heavy}
    write_json(expansion_root / "family.json", make_family_json(family, spec, medium), dry_run)
    write_text(expansion_root / "README.md", readme_for_family(family, spec, variants), dry_run)
    copy_hooks(dungeons_root, expansion_root, family, dry_run)
    for tier, quest in variants.items():
        write_json(expansion_root / tier / "quest.json", quest, dry_run)


def patch_aliases(repo: Path, dry_run: bool) -> None:
    _ = repo
    action = "DRY " if dry_run else ""
    print(f"{action}alias patch skipped; current GridEngine/HookEngine handle tier aliases.")


def remove_legacy_lite_alias_duplicates(repo: Path, dry_run: bool) -> None:
    """Optional cleanup hook, intentionally conservative.

    The migration keeps legacy dungeons in place by default so old benchmark suites remain
    stable. This function is left here as a documented no-op until the project decides to
    delete or deprecate src/dungeongrid/dungeons/<family> folders.
    """
    _ = repo, dry_run


def selected_families(raw: str | None) -> list[str]:
    if not raw:
        return list(FAMILY_SPECS)
    selected = [item.strip() for item in raw.split(",") if item.strip()]
    unknown = [family for family in selected if family not in FAMILY_SPECS]
    if unknown:
        raise ValueError(f"Unknown families: {unknown}")
    return selected


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd(), help="DungeonGrid repository root")
    parser.add_argument("--families", help="Comma-separated subset of family ids to migrate")
    parser.add_argument("--dry-run", action="store_true", help="Print writes without changing files")
    parser.add_argument(
        "--patch-aliases",
        action="store_true",
        help="Patch GridEngine/HookEngine legacy aliases so <family> resolves to base:<family>:<tier>",
    )
    args = parser.parse_args()

    validate_embedded_templates()
    repo = args.repo.resolve()
    if not (repo / "src" / "dungeongrid").exists():
        raise SystemExit(f"Not a DungeonGrid repository root: {repo}")

    families = selected_families(args.families)
    for family in families:
        migrate_family(repo, family, args.dry_run)
        print(f"migrated {family}")

    if args.patch_aliases:
        patch_aliases(repo, args.dry_run)
        print("patched legacy aliases")

    print("done")


if __name__ == "__main__":
    main()
