"""FastAPI entrypoint for the DungeonGrid Synth container runtime."""

from __future__ import annotations

import uvicorn

from synth_containers.http_adapter import create_reference_app

from .runtime import DungeonGridContainerRuntime


runtime = DungeonGridContainerRuntime()
app = create_reference_app(runtime, title="dungeongrid-container")


def main() -> None:
    uvicorn.run("dungeongrid.container.app:app", host="0.0.0.0", port=8080)


if __name__ == "__main__":
    main()
