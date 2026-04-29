"""Dungeon hook loading and execution utilities."""

from __future__ import annotations

import importlib.util
import json
import os
from dataclasses import dataclass
from importlib import resources
from pathlib import Path
from types import ModuleType
from typing import Any, Iterable

TIER_ORDER = ("pico", "lite", "medium", "heavy")


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
            "reward": max(0.0, float(reward)),
            "round": self.state.round,
        }
        if description:
            event["description"] = description
        self.state.achievements_unlocked.add(achievement_id)
        self.state.achievement_events.append(event)
        self.state.achievement_reward += max(0.0, float(reward))
        self.state.event_log.append(f"Achievement unlocked: {event['title']}.")
        return event


class HookEngine:
    """Loads and invokes optional per-dungeon Python hook modules."""

    def __init__(
        self,
        dungeon_dir: str | Path | None = None,
        expansion_paths: Iterable[str | Path] | None = None,
    ) -> None:
        self.dungeon_dir = Path(dungeon_dir) if dungeon_dir else None
        self.expansion_paths = tuple(
            Path(path).expanduser()
            for path in (
                expansion_paths
                if expansion_paths is not None
                else self._expansion_paths_from_env()
            )
        )
        self._modules: dict[str, tuple[ModuleType, ...]] = {}

    def load(self, quest_id: str) -> tuple[ModuleType, ...]:
        if quest_id not in self._modules:
            self._modules[quest_id] = self._load_modules(quest_id)
        return self._modules[quest_id]

    def call(self, quest_id: str, name: str, ctx: HookContext) -> Any:
        result = None
        for module in self.load(quest_id):
            func = getattr(module, name, None)
            if callable(func):
                result = func(ctx)
        return result

    def register(self, quest_id: str, registry: Any) -> None:
        for module in self.load(quest_id):
            func = getattr(module, "register", None)
            if callable(func):
                func(registry)

    def _load_modules(self, quest_id: str) -> tuple[ModuleType, ...]:
        modules: list[ModuleType] = []
        path = self._filesystem_hooks_path(quest_id)
        if path and path.exists():
            module = self._module_from_path(quest_id, path)
            return (module,) if module else ()

        for hook_resource in self._resource_hook_paths(quest_id):
            try:
                if not hook_resource.is_file():
                    continue
                with resources.as_file(hook_resource) as hook_path:
                    module = self._module_from_path(quest_id, hook_path)
                    if module:
                        modules.append(module)
            except (FileNotFoundError, ModuleNotFoundError):
                continue
        return tuple(modules)

    def _resource_hook_paths(self, quest_id: str) -> list[Any]:
        if self._is_tiered_quest_id(quest_id):
            namespace, family, tier = quest_id.split(":", 2)
            root = self._expansion_root(namespace)
            if root is None:
                return []
            layout = self._expansion_layout(root)
            if layout is None:
                return []
            family_root = root.joinpath(layout, family)
            return [
                root.joinpath("hooks.py"),
                family_root.joinpath("hooks.py"),
                family_root.joinpath(tier, "hooks.py"),
            ]
        return [resources.files("dungeongrid.dungeons").joinpath(quest_id, "hooks.py")]

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

    def _is_tiered_quest_id(self, quest_id: str) -> bool:
        parts = quest_id.split(":")
        return len(parts) == 3 and parts[2] in TIER_ORDER and self._expansion_root(parts[0]) is not None

    def _expansion_root(self, namespace: str) -> Any | None:
        if namespace == "base":
            try:
                return resources.files("dungeongrid").joinpath("expansions", "base")
            except (FileNotFoundError, ModuleNotFoundError):
                return None
        for current_namespace, root in self._iter_external_expansion_roots():
            if current_namespace == namespace:
                return root
        return None

    def _iter_external_expansion_roots(self) -> Iterable[tuple[str, Path]]:
        seen: set[Path] = set()
        for path in self.expansion_paths:
            if not path.exists():
                continue
            candidates = [path] if self._expansion_layout(path) else []
            candidates.extend(
                child
                for child in sorted(path.iterdir())
                if child.is_dir() and self._expansion_layout(child)
            )
            for candidate in candidates:
                resolved = candidate.resolve()
                if resolved in seen:
                    continue
                seen.add(resolved)
                yield self._expansion_namespace(candidate), candidate

    @staticmethod
    def _expansion_paths_from_env() -> tuple[Path, ...]:
        raw = os.environ.get("DUNGEONGRID_EXPANSION_PATHS", "")
        return tuple(Path(part) for part in raw.split(os.pathsep) if part)

    @staticmethod
    def _expansion_layout(root: Any) -> str | None:
        for layout in ("dungeons", "missions"):
            try:
                if root.joinpath(layout).is_dir():
                    return layout
            except FileNotFoundError:
                continue
        return None

    @staticmethod
    def _expansion_namespace(root: Path) -> str:
        for filename in ("manifest.json", "expansion.json"):
            path = root / filename
            if not path.is_file():
                continue
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            namespace = data.get("namespace") or data.get("id")
            if namespace:
                return str(namespace)
        return root.name

    def _module_from_path(self, quest_id: str, path: Path) -> ModuleType | None:
        module_name = f"_dungeongrid_hook_{quest_id}_{abs(hash(str(path)))}"
        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            return None
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
