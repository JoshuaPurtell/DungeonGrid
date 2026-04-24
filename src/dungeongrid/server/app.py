"""FastAPI server for DungeonGrid."""

from __future__ import annotations

import argparse
from typing import Any

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

from dungeongrid.env import DungeonGridEnvironment
from dungeongrid.models import DungeonGridAction, DungeonGridObservation, DungeonGridStep

app = FastAPI(title="DungeonGrid OpenEnv", version="0.1.0")
_env = DungeonGridEnvironment()


class ResetRequest(BaseModel):
    quest_id: str = "lantern_crypt"
    num_heroes: int = 4
    seed: int | None = None
    observation_mode: str = "mixed"


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "active_agent": _env.state.active_agent() if _env.state else None}


@app.post("/reset", response_model=DungeonGridObservation)
def reset(request: ResetRequest) -> DungeonGridObservation:
    return _env.reset(
        quest_id=request.quest_id,
        num_heroes=request.num_heroes,
        seed=request.seed,
        observation_mode=request.observation_mode,
    )


@app.get("/observe/{agent_id}", response_model=DungeonGridObservation)
def observe(agent_id: str) -> DungeonGridObservation:
    return _env.observe(agent_id)


@app.get("/legal_actions/{agent_id}")
def legal_actions(agent_id: str) -> dict[str, Any]:
    return {"agent_id": agent_id, "legal_actions": _env.legal_actions(agent_id)}


@app.post("/step", response_model=DungeonGridStep)
def step(action: DungeonGridAction) -> DungeonGridStep:
    return _env.step(action)


@app.get("/state")
def state(visibility: str = "omniscient") -> dict[str, Any]:
    return _env.state_json(visibility=visibility)


@app.get("/trace")
def trace() -> dict[str, Any]:
    return _env.export_trace()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    uvicorn.run(
        "dungeongrid.server.app:app",
        host=args.host,
        port=args.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
