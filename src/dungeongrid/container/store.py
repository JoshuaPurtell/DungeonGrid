"""Durable checkpoint storage for the DungeonGrid container runtime."""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from synth_containers.nouns import CheckpointDescriptor


class SQLiteDungeonGridCheckpointStore:
    """Small SQLite index for checkpoint descriptors and embedded checkpoint blobs."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()

    def save_checkpoint(self, descriptor: CheckpointDescriptor) -> None:
        payload = descriptor.to_dict()
        data = str((payload.get("metadata") or {}).get("checkpoint_data_base64") or "")
        with sqlite3.connect(str(self.path)) as conn:
            conn.execute(
                """
                INSERT INTO checkpoints (
                  checkpoint_id, rollout_id, descriptor_json, checkpoint_data_base64, updated_at
                )
                VALUES (?, ?, ?, ?, datetime('now'))
                ON CONFLICT(checkpoint_id) DO UPDATE SET
                  rollout_id = excluded.rollout_id,
                  descriptor_json = excluded.descriptor_json,
                  checkpoint_data_base64 = excluded.checkpoint_data_base64,
                  updated_at = excluded.updated_at
                """,
                (
                    descriptor.checkpoint_id,
                    descriptor.rollout_id,
                    json.dumps(payload, sort_keys=True),
                    data,
                ),
            )

    def load_checkpoint(self, checkpoint_id: str) -> tuple[CheckpointDescriptor, str] | None:
        with sqlite3.connect(str(self.path)) as conn:
            row = conn.execute(
                """
                SELECT descriptor_json, checkpoint_data_base64
                FROM checkpoints
                WHERE checkpoint_id = ?
                """,
                (checkpoint_id,),
            ).fetchone()
        if row is None:
            return None
        return self._descriptor_from_json(row[0]), str(row[1] or "")

    def list_checkpoints(self, rollout_id: str | None = None) -> list[tuple[CheckpointDescriptor, str]]:
        query = """
            SELECT descriptor_json, checkpoint_data_base64
            FROM checkpoints
        """
        params: tuple[Any, ...] = ()
        if rollout_id is not None:
            query += " WHERE rollout_id = ?"
            params = (rollout_id,)
        query += " ORDER BY updated_at DESC, checkpoint_id DESC"
        with sqlite3.connect(str(self.path)) as conn:
            rows = conn.execute(query, params).fetchall()
        return [(self._descriptor_from_json(row[0]), str(row[1] or "")) for row in rows]

    def _init_schema(self) -> None:
        with sqlite3.connect(str(self.path)) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS checkpoints (
                  checkpoint_id TEXT PRIMARY KEY,
                  rollout_id TEXT NOT NULL,
                  descriptor_json TEXT NOT NULL,
                  checkpoint_data_base64 TEXT NOT NULL,
                  updated_at TEXT NOT NULL DEFAULT (datetime('now'))
                )
                """
            )
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_dungeongrid_checkpoints_rollout
                ON checkpoints(rollout_id, updated_at)
                """
            )

    def _descriptor_from_json(self, text: str) -> CheckpointDescriptor:
        payload = json.loads(text)
        allowed = CheckpointDescriptor.__dataclass_fields__.keys()
        return CheckpointDescriptor(**{key: payload[key] for key in allowed if key in payload})
