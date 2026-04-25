"""Canonical DungeonGrid task catalog slices for container consumers."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

DUNGEONS: tuple[str, ...] = (
    "lantern_crypt",
    "bells_under_blackwater",
    "ashen_pantry",
    "cinder_exit",
    "low_shrine_locks",
    "trial_of_embers",
    "iron_captive",
    "tusk_warlord_lair",
    "magistrate_gold",
    "glass_maze",
    "broken_oath_ambush",
    "lost_apprentice",
    "cinder_mage_tower",
    "hourglass_escape",
    "veiled_castle",
    "black_standard_keep",
    "barrow_of_the_hollow_king",
    "moonblade_vault",
    "return_to_hollow_barrow",
    "frost_mirror_hold",
)

PLAYER_MODES: dict[str, int] = {
    "solo": 1,
    "duo": 2,
    "trio": 3,
    "squad": 4,
}

WARDEN_VARIANTS: tuple[str, ...] = ("scripted", "aggressive", "noisy")


@dataclass(frozen=True, slots=True)
class DungeonGridTaskEntry:
    task_instance_id: str
    task_id: str
    split: str
    quest_id: str
    player_mode: str
    num_heroes: int
    seed: int
    warden_variant: str = "scripted"

    def input_payload(self) -> dict[str, Any]:
        return {
            "quest_id": self.quest_id,
            "player_mode": self.player_mode,
            "num_heroes": self.num_heroes,
            "warden_variant": self.warden_variant,
        }

    def tags(self) -> list[str]:
        return [
            "dungeongrid",
            self.split,
            self.quest_id,
            self.player_mode,
            f"{self.num_heroes}_heroes",
            self.warden_variant,
        ]


def default_task_entries() -> list[DungeonGridTaskEntry]:
    entries: list[DungeonGridTaskEntry] = []
    split_seeds = {"train": (11, 13), "heldout": (101,)}
    for split, seeds in split_seeds.items():
        for quest_id in DUNGEONS:
            for player_mode, num_heroes in PLAYER_MODES.items():
                for seed in seeds:
                    entries.append(
                        DungeonGridTaskEntry(
                            task_instance_id=f"dungeongrid:{split}:{quest_id}:{player_mode}:{seed}",
                            task_id=f"dungeongrid.{quest_id}.{player_mode}",
                            split=split,
                            quest_id=quest_id,
                            player_mode=player_mode,
                            num_heroes=num_heroes,
                            seed=seed,
                        )
                    )
    return entries


def entry_by_id(task_instance_id: str | None, *, seed: int | None = None) -> DungeonGridTaskEntry:
    entries = default_task_entries()
    if task_instance_id:
        for entry in entries:
            if entry.task_instance_id == task_instance_id:
                return entry
        raise KeyError(f"unknown DungeonGrid task instance: {task_instance_id}")
    if seed is None:
        return entries[0]
    return entries[int(seed) % len(entries)]
