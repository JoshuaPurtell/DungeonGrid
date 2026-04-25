"""Dungeon hook loading and execution utilities."""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from types import ModuleType
from typing import Any


@dataclass(slots=True)
class HookContext:
    """Context passed to optional dungeon hook functions."""

    state: Any
    env: Any | None = None
    action: dict[str, Any] | None = None
    result: Any | None = None
    plan_result: Any | None = None

    def emit(self, message: str) -> None:
        self.state.event_log.append(str(message))

    def unlock_achievement(
        self,
        achievement_id: str,
        title: str | None = None,
        reward: float = 0.0,
        *,
        layer: str = "quest",
        description: str = "",
    ) -> dict[str, Any]:
        if "." not in achievement_id:
            achievement_id = f"{self.state.quest_id}.{achievement_id}"
        if achievement_id in self.state.achievements_unlocked:
            return {}
        event = {
            "id": achievement_id,
            "title": title or achievement_id.rsplit(".", 1)[-1].replace("_", " ").title(),
            "layer": layer,
            "reward": float(reward),
            "round": self.state.round,
        }
        if description:
            event["description"] = description
        self.state.achievements_unlocked.add(achievement_id)
        self.state.achievement_events.append(event)
        self.state.achievement_reward += float(reward)
        self.state.event_log.append(f"Achievement unlocked: {event['title']}.")
        return event


class HookEngine:
    """Loads and invokes optional per-dungeon Python hook modules."""

    def __init__(self, dungeon_dir: str | Path | None = None) -> None:
        self.dungeon_dir = Path(dungeon_dir) if dungeon_dir else None
        self._modules: dict[str, ModuleType | None] = {}

    def load(self, quest_id: str) -> ModuleType | None:
        if quest_id not in self._modules:
            self._modules[quest_id] = self._load_module(quest_id)
        return self._modules[quest_id]

    def call(self, quest_id: str, name: str, ctx: HookContext) -> Any:
        module = self.load(quest_id)
        func = getattr(module, name, None) if module else None
        if not callable(func):
            return None
        return func(ctx)

    def register(self, quest_id: str, registry: Any) -> None:
        module = self.load(quest_id)
        func = getattr(module, "register", None) if module else None
        if callable(func):
            func(registry)

    def _load_module(self, quest_id: str) -> ModuleType | None:
        path = self._filesystem_hooks_path(quest_id)
        if path and path.exists():
            return self._module_from_path(quest_id, path)

        try:
            hook_resource = resources.files("dungeongrid.dungeons").joinpath(quest_id, "hooks.py")
            if not hook_resource.is_file():
                return None
            with resources.as_file(hook_resource) as hook_path:
                return self._module_from_path(quest_id, hook_path)
        except (FileNotFoundError, ModuleNotFoundError):
            return None

    def _filesystem_hooks_path(self, quest_id: str) -> Path | None:
        if not self.dungeon_dir:
            return None
        folder_path = self.dungeon_dir / quest_id / "hooks.py"
        if folder_path.exists():
            return folder_path
        flat_path = self.dungeon_dir / f"{quest_id}_hooks.py"
        if flat_path.exists():
            return flat_path
        return None

    def _module_from_path(self, quest_id: str, path: Path) -> ModuleType | None:
        module_name = f"_dungeongrid_hook_{quest_id}_{abs(hash(str(path)))}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
