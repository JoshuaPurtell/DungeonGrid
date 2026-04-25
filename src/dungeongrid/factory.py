"""Stable public environment factory."""

from __future__ import annotations

from .env import DungeonGridEnvironment

SUPPORTED_ENV_NAMES = {
    "DungeonGrid-v0",
    "DungeonGrid-Text-v0",
    "DungeonGrid-OpenEnv-v0",
}


def make_dungeongrid_env_from_name(
    name: str = "DungeonGrid-v0",
    **kwargs,
) -> DungeonGridEnvironment:
    """Create a DungeonGrid environment by stable public name."""
    if name not in SUPPORTED_ENV_NAMES:
        supported = ", ".join(sorted(SUPPORTED_ENV_NAMES))
        raise ValueError(f"Unknown DungeonGrid environment {name!r}. Supported: {supported}")
    return DungeonGridEnvironment(**kwargs)
