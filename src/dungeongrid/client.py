"""Small HTTP client for the DungeonGrid FastAPI server."""

from __future__ import annotations

from typing import Any

import requests

from .models import DungeonGridAction, DungeonGridObservation, DungeonGridStep, model_to_dict


class DungeonGridClient:
    def __init__(self, base_url: str = "http://localhost:8000", timeout: float = 15.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def reset(self, quest_id: str = "lantern_crypt", num_heroes: int = 4, seed: int | None = None) -> DungeonGridObservation:
        payload = {"quest_id": quest_id, "num_heroes": num_heroes, "seed": seed}
        response = requests.post(f"{self.base_url}/reset", json=payload, timeout=self.timeout)
        response.raise_for_status()
        return DungeonGridObservation(**response.json())

    def observe(self, agent_id: str) -> DungeonGridObservation:
        response = requests.get(f"{self.base_url}/observe/{agent_id}", timeout=self.timeout)
        response.raise_for_status()
        return DungeonGridObservation(**response.json())

    def legal_actions(self, agent_id: str) -> list[dict[str, Any]]:
        response = requests.get(f"{self.base_url}/legal_actions/{agent_id}", timeout=self.timeout)
        response.raise_for_status()
        return response.json()["legal_actions"]

    def step(self, action: DungeonGridAction | dict[str, Any]) -> DungeonGridStep:
        response = requests.post(f"{self.base_url}/step", json=model_to_dict(action), timeout=self.timeout)
        response.raise_for_status()
        return DungeonGridStep(**response.json())

    def state(self, visibility: str = "omniscient") -> dict[str, Any]:
        response = requests.get(f"{self.base_url}/state", params={"visibility": visibility}, timeout=self.timeout)
        response.raise_for_status()
        return response.json()

    def trace(self) -> dict[str, Any]:
        response = requests.get(f"{self.base_url}/trace", timeout=self.timeout)
        response.raise_for_status()
        return response.json()
