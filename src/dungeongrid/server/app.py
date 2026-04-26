"""FastAPI server for DungeonGrid."""

from __future__ import annotations

import argparse
from typing import Any

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel

from dungeongrid.contracts import dungeongrid_rules
from dungeongrid.env import DungeonGridEnvironment
from dungeongrid.models import (
    DungeonGridAction,
    DungeonGridObservation,
    DungeonGridPlanResult,
    DungeonGridStep,
)

app = FastAPI(title="DungeonGrid OpenEnv", version="0.1.0")
_env = DungeonGridEnvironment()


class ResetRequest(BaseModel):
    quest_id: str = "lantern_crypt"
    num_heroes: int = 3
    seed: int | None = None
    observation_mode: str = "mixed"


class PlanRequest(BaseModel):
    intent: str | None = None
    actions: list[dict[str, Any]]
    agent_id: str | None = None


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


@app.post("/step", response_model=DungeonGridStep)
def step(action: DungeonGridAction) -> DungeonGridStep:
    return _env.step(action)


@app.post("/act_plan", response_model=DungeonGridPlanResult)
def act_plan(request: PlanRequest) -> DungeonGridPlanResult:
    return _env.act_plan(request.actions, intent=request.intent, agent_id=request.agent_id)


@app.get("/rules/{topic}")
def rules(topic: str) -> dict[str, Any]:
    return {"topic": topic, "text": dungeongrid_rules(topic)}


@app.get("/state")
def state(visibility: str = "omniscient") -> dict[str, Any]:
    return _env.state_json(visibility=visibility)


@app.get("/public_state")
def public_state() -> dict[str, Any]:
    return _env.public_state_json()


@app.get("/private_state")
def private_state() -> dict[str, Any]:
    return _env.private_state_json()


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
