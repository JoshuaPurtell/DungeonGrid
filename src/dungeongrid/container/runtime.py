"""Synth Containers managed runtime for DungeonGrid.

The runtime deliberately wraps the public DungeonGrid environment instead of
adding a second game API. Synth/Go-Explore consumers get catalog, rollout,
trace, checkpoint, and resume routes through synth_containers.http_adapter.
"""

from __future__ import annotations

import base64
import pickle
import uuid
from collections.abc import Mapping
from datetime import datetime, timezone
from typing import Any

from synth_containers.capabilities import (
    DatasetDescriptor,
    RuntimeCapabilitySurface,
    RuntimeMetadata,
    TaskCatalog,
    TaskInfo,
)
from synth_containers.nouns import (
    Actor,
    ArtifactDescriptor,
    CheckpointDescriptor,
    ExecutionRecord,
    Observation,
    Outcome,
    StateSnapshot,
    TaskDefinition,
    TaskInstance,
    ToolCallRecord,
    TraceEvent,
    Trajectory,
    TurnRecord,
)
from synth_containers.ontology import (
    CapabilityLevel,
    CheckpointSemantics,
    CoreNoun,
    ExecutionProfile,
    PrimitiveProtocol,
    ResumeSemantics,
    RolloutMode,
    RuntimeKind,
    StatefulnessTier,
)
from synth_containers.tool_runtime import (
    ToolCallSchemaKind,
    ToolOutputMode,
    ToolRuntimeCapabilities,
    ToolRuntimeKind,
)

from dungeongrid import DungeonGridEnvironment
from dungeongrid import __version__ as DUNGEONGRID_VERSION
from dungeongrid.core.agent_engine import AchievementScoutPolicy, GreedyHeroPolicy
from dungeongrid.env import CHECKPOINT_VERSION
from dungeongrid.models import model_to_dict

from .store import SQLiteDungeonGridCheckpointStore
from .task_sets import PLAYER_MODES, default_task_entries, entry_by_id

DEFAULT_MAX_STEPS = 40
AGENT_ENV_CHECKPOINT_VERSION = "dungeongrid.agent_env_checkpoint.v1"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _dump_checkpoint_payload(
    env: DungeonGridEnvironment,
    config: dict[str, Any],
    *,
    agent_state: dict[str, Any] | None = None,
    rollout_state: dict[str, Any] | None = None,
) -> str:
    env_payload = env.checkpoint_payload(
        {
            "dungeongrid_version": DUNGEONGRID_VERSION,
            "config": dict(config),
            "checkpoint_semantics": "true_environment_snapshot",
        }
    )
    envelope = {
        "version": AGENT_ENV_CHECKPOINT_VERSION,
        "dungeongrid_version": DUNGEONGRID_VERSION,
        "checkpoint_semantics": "agent_and_environment_snapshot",
        "env_checkpoint": env_payload,
        "agent_state": dict(agent_state or {}),
        "rollout_state": dict(rollout_state or {}),
        "config": dict(config),
    }
    return base64.b64encode(pickle.dumps(envelope, protocol=pickle.HIGHEST_PROTOCOL)).decode(
        "ascii"
    )


def _load_checkpoint_payload(data: str) -> dict[str, Any]:
    envelope = _load_checkpoint_envelope(data)
    payload = envelope.get("env_checkpoint")
    if not isinstance(payload, dict) or payload.get("version") != CHECKPOINT_VERSION:
        raise ValueError("unsupported DungeonGrid checkpoint payload")
    return payload


def _load_checkpoint_envelope(data: str) -> dict[str, Any]:
    payload = DungeonGridEnvironment()._decode_checkpoint(data)
    if not isinstance(payload, dict):
        raise ValueError("unsupported DungeonGrid checkpoint payload")
    if payload.get("version") == AGENT_ENV_CHECKPOINT_VERSION:
        env_payload = payload.get("env_checkpoint")
        if not isinstance(env_payload, dict) or env_payload.get("version") != CHECKPOINT_VERSION:
            raise ValueError("unsupported DungeonGrid env checkpoint in agent envelope")
        return payload
    if payload.get("version") != CHECKPOINT_VERSION:
        raise ValueError("unsupported DungeonGrid checkpoint payload")
    metadata = dict(payload.get("metadata") or {})
    return {
        "version": AGENT_ENV_CHECKPOINT_VERSION,
        "dungeongrid_version": metadata.get("dungeongrid_version") or DUNGEONGRID_VERSION,
        "checkpoint_semantics": "true_environment_snapshot",
        "env_checkpoint": payload,
        "agent_state": {},
        "rollout_state": {},
        "config": dict(metadata.get("config") or {}),
        "legacy_env_checkpoint": True,
    }


class DungeonGridContainerRuntime:
    """In-memory managed runtime with true DungeonGrid state snapshots."""

    def __init__(self, store_path: str | None = None) -> None:
        self._executions: dict[str, ExecutionRecord] = {}
        self._envs: dict[str, DungeonGridEnvironment] = {}
        self._checkpoints: dict[str, CheckpointDescriptor] = {}
        self._checkpoint_data: dict[str, str] = {}
        self._store = SQLiteDungeonGridCheckpointStore(store_path) if store_path else None

    def metadata(self) -> RuntimeMetadata:
        capabilities = RuntimeCapabilitySurface(
            runtime_kind=RuntimeKind.ENVIRONMENT,
            profiles=[
                ExecutionProfile.GYM_STYLE_ENVIRONMENT,
                ExecutionProfile.CHECKPOINTABLE_LONG_HORIZON_ENVIRONMENT,
                ExecutionProfile.MULTI_AGENT_LONG_HORIZON_ENVIRONMENT,
                ExecutionProfile.RL_TRAJECTORY_EMITTER,
            ],
            rollout_modes=[RolloutMode.BLOCKING, RolloutMode.ASYNC],
            statefulness_tier=StatefulnessTier.LONG_HORIZON,
            noun_fidelity={
                CoreNoun.TASK: CapabilityLevel.NATIVE,
                CoreNoun.TASK_INSTANCE: CapabilityLevel.NATIVE,
                CoreNoun.ACTOR: CapabilityLevel.NATIVE,
                CoreNoun.ACTION: CapabilityLevel.NATIVE,
                CoreNoun.OBSERVATION: CapabilityLevel.NATIVE,
                CoreNoun.STATE: CapabilityLevel.NATIVE,
                CoreNoun.CHECKPOINT: CapabilityLevel.NATIVE,
                CoreNoun.TRACE: CapabilityLevel.NATIVE,
                CoreNoun.REWARD: CapabilityLevel.NATIVE,
                CoreNoun.TOOL: CapabilityLevel.NATIVE,
            },
            protocol_fidelity={
                PrimitiveProtocol.CATALOG_BACKED: CapabilityLevel.NATIVE,
                PrimitiveProtocol.RESETTABLE: CapabilityLevel.NATIVE,
                PrimitiveProtocol.STEPPABLE: CapabilityLevel.NATIVE,
                PrimitiveProtocol.OBSERVABLE: CapabilityLevel.NATIVE,
                PrimitiveProtocol.STATE_READABLE: CapabilityLevel.NATIVE,
                PrimitiveProtocol.CHECKPOINTABLE: CapabilityLevel.NATIVE,
                PrimitiveProtocol.RESTORABLE: CapabilityLevel.NATIVE,
                PrimitiveProtocol.FORKABLE: CapabilityLevel.NATIVE,
                PrimitiveProtocol.ROLLOUT_RUNNABLE: CapabilityLevel.NATIVE,
                PrimitiveProtocol.ASYNC_ROLLOUT_RUNNABLE: CapabilityLevel.NATIVE,
                PrimitiveProtocol.TRACE_EMITTING: CapabilityLevel.NATIVE,
                PrimitiveProtocol.REWARD_EMITTING: CapabilityLevel.NATIVE,
                PrimitiveProtocol.TOOL_CALLABLE: CapabilityLevel.NATIVE,
                PrimitiveProtocol.MULTI_ACTOR: CapabilityLevel.NATIVE,
            },
            checkpoint_semantics=CheckpointSemantics.TRUE_ENVIRONMENT_SNAPSHOT,
            restore_semantics="true_environment_snapshot",
            resume_semantics=ResumeSemantics.TRUE_ENVIRONMENT_SNAPSHOT,
            checkpoint_support=True,
            resume_support=True,
            terminate_support=True,
            state_support=True,
            trace_support=True,
            reward_support=True,
            artifact_support=True,
            multi_actor=True,
            supports_branching=True,
            true_environment_snapshot=True,
            tool_runtime=ToolRuntimeCapabilities(
                runtime_kind=ToolRuntimeKind.PROVIDER_NATIVE_TOOLS,
                schema_kind=ToolCallSchemaKind.OPENAI_CHAT_FUNCTIONS,
                output_mode=ToolOutputMode.TOOL_REQUIRED,
                metadata={
                    "tools": [
                        {
                            "tool_name": "dungeongrid_act",
                            "description": "Submit a queued JSON action plan for the active DungeonGrid hero.",
                            "input_schema": {
                                "type": "object",
                                "properties": {
                                    "intent": {"type": "string"},
                                    "actions": {"type": "array", "items": {"type": "object"}},
                                },
                                "required": ["actions"],
                            },
                        },
                        {
                            "tool_name": "dungeongrid_rules",
                            "description": "Read compact DungeonGrid rules by topic.",
                            "input_schema": {
                                "type": "object",
                                "properties": {"topic": {"type": "string"}},
                                "required": ["topic"],
                            },
                        },
                    ]
                },
            ),
            metadata={
                "environment": "dungeongrid",
                "dungeongrid_version": DUNGEONGRID_VERSION,
                "checkpoint_version": CHECKPOINT_VERSION,
                "agent_env_checkpoint_version": AGENT_ENV_CHECKPOINT_VERSION,
                "action_contract": "OpenEnv ReAct JSON action plans",
            },
        )
        return RuntimeMetadata(
            runtime_id="dungeongrid-container",
            name="DungeonGrid Container Runtime",
            description="Branchable multi-agent DungeonGrid runtime for Synth Containers and Go-Explore.",
            capabilities=capabilities,
            metadata={"package": "dungeongrid"},
        )

    def task_info(self) -> TaskInfo:
        return TaskInfo(
            task=TaskDefinition(
                task_id="dungeongrid",
                task_name="DungeonGrid multi-agent dungeon crawl",
                task_family="dungeongrid",
                benchmark="dungeongrid",
                version=DUNGEONGRID_VERSION,
                metadata={"player_modes": dict(PLAYER_MODES)},
            ),
            dataset=DatasetDescriptor(
                dataset_id="dungeongrid_fixed_quests_v1",
                visible_splits=["train", "heldout"],
                default_split="train",
                row_count=len(default_task_entries()),
            ),
            capabilities=self.metadata().capabilities,
            limits={"default_max_steps": DEFAULT_MAX_STEPS},
            environment="dungeongrid",
            task_metadata={
                "dungeons": sorted({entry.quest_id for entry in default_task_entries()})
            },
        )

    async def task_catalog(self) -> TaskCatalog:
        entries = default_task_entries()
        task_defs: dict[str, TaskDefinition] = {}
        instances: list[TaskInstance] = []
        for entry in entries:
            task_defs.setdefault(
                entry.task_id,
                TaskDefinition(
                    task_id=entry.task_id,
                    task_name=f"DungeonGrid {entry.quest_id} {entry.player_mode}",
                    task_family="dungeongrid",
                    benchmark="dungeongrid",
                    version=DUNGEONGRID_VERSION,
                    metadata={
                        "quest_id": entry.quest_id,
                        "player_mode": entry.player_mode,
                        "num_heroes": entry.num_heroes,
                    },
                ),
            )
            instances.append(
                TaskInstance(
                    task_instance_id=entry.task_instance_id,
                    task_id=entry.task_id,
                    split=entry.split,
                    seed=entry.seed,
                    input_payload=entry.input_payload(),
                    tags=entry.tags(),
                )
            )
        return TaskCatalog(
            catalog_id="dungeongrid.fixed_quests.v1",
            tasks=list(task_defs.values()),
            instances=instances,
            metadata={"task_family": "dungeongrid"},
        )

    async def submit_rollout(self, request: Mapping[str, Any]) -> ExecutionRecord:
        rollout_id = str(
            request.get("rollout_id") or f"dungeongrid_rollout_{uuid.uuid4().hex[:10]}"
        )
        trace_correlation_id = str(request.get("trace_correlation_id") or rollout_id)
        task_instance_id = str(request.get("task_instance_id") or "").strip() or None
        seed = _coerce_int(
            (request.get("env") or {}).get("seed")
            if isinstance(request.get("env"), Mapping)
            else None
        )
        entry = entry_by_id(task_instance_id, seed=seed)
        env, config, parent_checkpoint_id = self._env_from_request(request, entry)
        max_steps = _max_steps(request, default=DEFAULT_MAX_STEPS)
        policy_kind = _policy_kind(request)
        execution = self._run_env(
            rollout_id=rollout_id,
            trace_correlation_id=trace_correlation_id,
            entry=entry,
            env=env,
            config=config,
            max_steps=max_steps,
            policy_kind=policy_kind,
            agent_state=dict(config.pop("_agent_state", {}) or {}),
            rollout_state=dict(config.pop("_rollout_state", {}) or {}),
            parent_rollout_id=str(request.get("parent_rollout_id") or "") or None,
            parent_checkpoint_id=parent_checkpoint_id,
            trial_id=str(request.get("trial_id") or "") or None,
        )
        self._executions[rollout_id] = execution
        self._envs[rollout_id] = env
        return execution

    async def get_execution(self, rollout_id: str) -> ExecutionRecord | None:
        return self._executions.get(rollout_id)

    async def get_execution_state(self, rollout_id: str) -> ExecutionRecord | None:
        return self._executions.get(rollout_id)

    async def terminate_execution(
        self, rollout_id: str, request: Mapping[str, Any]
    ) -> ExecutionRecord | None:
        execution = self._executions.get(rollout_id)
        if execution is None:
            return None
        execution.status = "terminated"
        execution.success_status = "terminated"
        execution.updated_at = _utc_now_iso()
        execution.metadata["terminate_reason"] = str(request.get("reason") or "")
        return execution

    async def pause_execution(
        self, rollout_id: str, request: Mapping[str, Any]
    ) -> ExecutionRecord | None:
        execution = self._executions.get(rollout_id)
        if execution is None:
            return None
        execution.status = "paused"
        execution.updated_at = _utc_now_iso()
        execution.metadata["pause_reason"] = str(request.get("reason") or "")
        return execution

    async def create_checkpoint(
        self, rollout_id: str, request: Mapping[str, Any]
    ) -> CheckpointDescriptor | None:
        env = self._envs.get(rollout_id)
        execution = self._executions.get(rollout_id)
        if env is None or execution is None:
            return None
        descriptor = self._store_checkpoint(
            rollout_id=rollout_id,
            env=env,
            config=dict(execution.metadata.get("env_config") or {}),
            agent_state=dict(execution.metadata.get("agent_state") or {}),
            rollout_state=dict(execution.metadata.get("rollout_state") or {}),
            checkpoint_id=str(request.get("checkpoint_id") or "") or None,
            label=str(request.get("label") or "") or None,
            labels=[str(item) for item in request.get("labels", []) or []],
            actor_ids=[str(item) for item in request.get("actor_ids", []) or []],
            metadata=dict(request.get("metadata") or {}),
            annotations=dict(request.get("annotations") or {}),
        )
        execution.checkpoint = descriptor
        execution.summary["checkpoint_id"] = descriptor.checkpoint_id
        return descriptor

    async def list_checkpoints(self, rollout_id: str | None = None) -> list[CheckpointDescriptor]:
        if self._store is not None:
            for descriptor, data in self._store.list_checkpoints(rollout_id):
                self._checkpoints.setdefault(descriptor.checkpoint_id, descriptor)
                if data:
                    self._checkpoint_data.setdefault(descriptor.checkpoint_id, data)
        if rollout_id is None:
            return list(self._checkpoints.values())
        return [item for item in self._checkpoints.values() if item.rollout_id == rollout_id]

    async def get_checkpoint(self, checkpoint_id: str) -> CheckpointDescriptor | None:
        checkpoint = self._checkpoints.get(checkpoint_id)
        if checkpoint is not None:
            return checkpoint
        if self._store is None:
            return None
        loaded = self._store.load_checkpoint(checkpoint_id)
        if loaded is None:
            return None
        descriptor, data = loaded
        self._checkpoints[checkpoint_id] = descriptor
        if data:
            self._checkpoint_data[checkpoint_id] = data
        return descriptor

    async def get_rollout_checkpoint(
        self, rollout_id: str, checkpoint_id: str
    ) -> CheckpointDescriptor | None:
        checkpoint = await self.get_checkpoint(checkpoint_id)
        if checkpoint is None or checkpoint.rollout_id != rollout_id:
            return None
        return checkpoint

    async def update_checkpoint_labels(
        self, checkpoint_id: str, request: Mapping[str, Any]
    ) -> CheckpointDescriptor | None:
        checkpoint = self._checkpoints.get(checkpoint_id)
        if checkpoint is None:
            return None
        labels = [str(item) for item in request.get("labels", []) or []]
        checkpoint.labels = list(dict.fromkeys([*checkpoint.labels, *labels]))
        checkpoint.annotations.update(dict(request.get("annotations") or {}))
        checkpoint.metadata.update(dict(request.get("metadata") or {}))
        return checkpoint

    async def resume_execution(
        self, rollout_id: str, request: Mapping[str, Any]
    ) -> ExecutionRecord | None:
        checkpoint_id = str(request.get("checkpoint_id") or "").strip()
        if not checkpoint_id:
            source_execution = self._executions.get(rollout_id)
            if source_execution and source_execution.checkpoint:
                checkpoint_id = source_execution.checkpoint.checkpoint_id
        checkpoint_ref = (
            request.get("checkpoint") if isinstance(request.get("checkpoint"), Mapping) else None
        )
        checkpoint_data = self._checkpoint_data_for_id(checkpoint_id)
        if checkpoint_data is None:
            checkpoint_data = self._checkpoint_data_from_ref(checkpoint_ref)
        if not checkpoint_id and checkpoint_ref:
            checkpoint_id = str(checkpoint_ref.get("checkpoint_id") or "").strip()
        if not checkpoint_id or checkpoint_data is None:
            return None
        checkpoint = self._checkpoints.get(checkpoint_id)
        envelope = _load_checkpoint_envelope(checkpoint_data)
        payload = envelope["env_checkpoint"]
        env = DungeonGridEnvironment()
        env.restore_checkpoint(payload)
        metadata = dict(payload.get("metadata") or {})
        config = dict(envelope.get("config") or metadata.get("config") or {})
        agent_state = dict(envelope.get("agent_state") or {})
        rollout_state = dict(envelope.get("rollout_state") or {})
        overrides = (
            request.get("overrides") if isinstance(request.get("overrides"), Mapping) else {}
        )
        max_steps = (
            _coerce_int(overrides.get("continue_steps") or overrides.get("segment_steps"))
            or DEFAULT_MAX_STEPS
        )
        target_rollout_id = str(
            request.get("target_rollout_id") or f"dungeongrid_branch_{uuid.uuid4().hex[:10]}"
        )
        entry = entry_by_id(
            str(config.get("task_instance_id") or "") or None, seed=_coerce_int(config.get("seed"))
        )
        execution = self._run_env(
            rollout_id=target_rollout_id,
            trace_correlation_id=str(request.get("trace_correlation_id") or target_rollout_id),
            entry=entry,
            env=env,
            config=config,
            max_steps=max_steps,
            policy_kind=str((overrides.get("policy") or {}).get("kind") or "achievement_scout")
            if isinstance(overrides.get("policy"), Mapping)
            else str(agent_state.get("policy_kind") or "achievement_scout"),
            agent_state=agent_state,
            rollout_state=rollout_state,
            parent_rollout_id=(
                checkpoint.rollout_id
                if checkpoint
                else str((checkpoint_ref or {}).get("rollout_id") or "") or None
            ),
            parent_checkpoint_id=checkpoint_id,
            trial_id=None,
        )
        self._executions[target_rollout_id] = execution
        self._envs[target_rollout_id] = env
        return execution

    def _env_from_request(
        self, request: Mapping[str, Any], entry: Any
    ) -> tuple[DungeonGridEnvironment, dict[str, Any], str | None]:
        checkpoint_ref = request.get("checkpoint")
        checkpoint_id = checkpoint_ref if isinstance(checkpoint_ref, str) else None
        if isinstance(checkpoint_ref, Mapping):
            checkpoint_id = str(checkpoint_ref.get("checkpoint_id") or "").strip() or None
        checkpoint_data = self._checkpoint_data_for_id(checkpoint_id or "")
        if checkpoint_data is None and isinstance(checkpoint_ref, Mapping):
            checkpoint_data = self._checkpoint_data_from_ref(checkpoint_ref)
        if checkpoint_data is not None:
            envelope = _load_checkpoint_envelope(checkpoint_data)
            payload = envelope["env_checkpoint"]
            env = DungeonGridEnvironment()
            env.restore_checkpoint(payload)
            metadata = dict(payload.get("metadata") or {})
            config = dict(envelope.get("config") or metadata.get("config") or {})
            config["_agent_state"] = dict(envelope.get("agent_state") or {})
            config["_rollout_state"] = dict(envelope.get("rollout_state") or {})
            return env, config, checkpoint_id

        env_config = request.get("env") if isinstance(request.get("env"), Mapping) else {}
        raw_config = (
            env_config.get("config") if isinstance(env_config.get("config"), Mapping) else {}
        )
        quest_id = str(raw_config.get("quest_id") or env_config.get("quest_id") or entry.quest_id)
        player_mode = str(
            raw_config.get("player_mode") or env_config.get("player_mode") or entry.player_mode
        )
        num_heroes = (
            _coerce_int(raw_config.get("num_heroes") or env_config.get("num_heroes"))
            or entry.num_heroes
        )
        seed = _coerce_int(env_config.get("seed") or raw_config.get("seed")) or entry.seed
        observation_mode = str(raw_config.get("observation_mode") or "mixed")
        env = DungeonGridEnvironment()
        env.reset(
            quest_id=quest_id, num_heroes=num_heroes, seed=seed, observation_mode=observation_mode
        )
        config = {
            "task_instance_id": entry.task_instance_id,
            "task_id": entry.task_id,
            "quest_id": quest_id,
            "player_mode": player_mode,
            "num_heroes": num_heroes,
            "seed": seed,
            "observation_mode": observation_mode,
        }
        return env, config, None

    def _run_env(
        self,
        *,
        rollout_id: str,
        trace_correlation_id: str,
        entry: Any,
        env: DungeonGridEnvironment,
        config: dict[str, Any],
        max_steps: int,
        policy_kind: str,
        agent_state: dict[str, Any] | None,
        rollout_state: dict[str, Any] | None,
        parent_rollout_id: str | None,
        parent_checkpoint_id: str | None,
        trial_id: str | None,
    ) -> ExecutionRecord:
        created = _utc_now_iso()
        turns: list[TurnRecord] = []
        events: list[TraceEvent] = []
        actors = [
            Actor(actor_id=hero_id, role=hero.role, display_name=hero.role.title())
            for hero_id, hero in env.state.heroes.items()
        ]
        policy = _make_policy(policy_kind)
        restored_policy_state = dict((agent_state or {}).get("hero_policy_state") or {})
        restore_state = getattr(policy, "restore_state", None)
        if callable(restore_state) and restored_policy_state:
            restore_state(restored_policy_state)
        previous_rollout_state = dict(rollout_state or {})
        previous_turn_count = int(previous_rollout_state.get("turn_count", 0) or 0)
        previous_total_reward = float(previous_rollout_state.get("total_reward", 0.0) or 0.0)
        total_reward = previous_total_reward
        for turn_index in range(max_steps):
            if env.state.done:
                break
            active = env.state.active_agent()
            obs = env.observe(active)
            legal = env._legal_actions(active)
            action = policy.act({"legal_actions": legal, "symbolic": obs.symbolic})
            result = env.act_plan([action], intent=f"{policy_kind}:{active}", agent_id=active)
            total_reward += float(result.reward)
            executed = [item.get("action") for item in result.executed_actions]
            skipped = [item.get("action") for item in result.skipped_actions]
            turn = TurnRecord(
                turn_index=turn_index,
                actor_id=active,
                prompt_messages=[{"role": "user", "content": obs.text}],
                actions=[action],
                executed_actions=executed,
                observation=Observation(
                    content=result.observation.text,
                    actor_id=result.observation.agent_id,
                    channels={
                        "text": result.observation.text,
                        "visible_map": result.observation.visible_map,
                        "symbolic": result.observation.symbolic,
                    },
                    metadata={
                        "active_agent": result.observation.active_agent,
                        "quest_id": env.state.quest_id,
                    },
                ),
                event_rewards=[float(result.reward)],
                tool_calls=[
                    ToolCallRecord(
                        tool_name="dungeongrid_act",
                        arguments={"intent": result.intent, "actions": result.submitted_actions},
                        result=model_to_dict(result),
                        success=True,
                    )
                ],
                metadata={
                    "submitted_action_count": len(result.submitted_actions),
                    "executed_action_count": len(result.executed_actions),
                    "skipped_action_count": len(result.skipped_actions),
                    "skipped_actions": skipped,
                    "reveal_stopped": result.reveal_stopped,
                    "reveal_reason": result.reveal_reason,
                    "new_achievements": result.new_achievements,
                },
            )
            turns.append(turn)
            events.append(
                TraceEvent(
                    event_type="dungeongrid_plan",
                    at=_utc_now_iso(),
                    event_id=f"{rollout_id}_event_{turn_index}",
                    step_index=previous_turn_count + turn_index,
                    actor_id=active,
                    payload={
                        "action": action,
                        "executed_actions": executed,
                        "skipped_actions": skipped,
                        "reward": float(result.reward),
                        "done": bool(result.done),
                        "reveal_reason": result.reveal_reason,
                    },
                )
            )
        metrics = env.agent_engine.metrics(env.state)
        transcript = env.export_transcript()
        summary = {
            **metrics,
            "total_reward": round(total_reward, 4),
            "quest_id": env.state.quest_id,
            "player_mode": config.get("player_mode"),
            "num_heroes": len(env.state.heroes),
            "step_count": previous_turn_count + len(turns),
            "segment_step_count": len(turns),
            "success": bool(env.state.done and env.state.winner == "heroes"),
            "cell_key": self._cell_key(env),
        }
        agent_snapshot = {
            "schema_version": "dungeongrid.container_agent_state.v1",
            "policy_kind": policy_kind,
            "hero_policy_class": type(policy).__name__,
            "hero_policy_state": _snapshot_policy_state(policy),
        }
        rollout_snapshot = {
            "schema_version": "dungeongrid.container_rollout_state.v1",
            "rollout_id": rollout_id,
            "turn_count": previous_turn_count + len(turns),
            "segment_turn_count": len(turns),
            "total_reward": round(total_reward, 4),
            "previous_total_reward": round(previous_total_reward, 4),
            "parent_rollout_id": parent_rollout_id,
            "parent_checkpoint_id": parent_checkpoint_id,
            "last_actor_id": turns[-1].actor_id if turns else None,
        }
        checkpoint = self._store_checkpoint(
            rollout_id=rollout_id,
            env=env,
            config=config,
            agent_state=agent_snapshot,
            rollout_state=rollout_snapshot,
            checkpoint_id=None,
            label="final" if env.state.done else "frontier",
            labels=["final" if env.state.done else "frontier", str(summary["cell_key"])],
            actor_ids=[actor.actor_id for actor in actors],
            metadata={
                "cell_key": summary["cell_key"],
                "step_count": previous_turn_count + len(turns),
                "segment_step_count": len(turns),
                "env_config": dict(config),
            },
            annotations={"metrics": metrics},
        )
        summary["checkpoint_id"] = checkpoint.checkpoint_id
        execution = ExecutionRecord(
            execution_id=rollout_id,
            trace_correlation_id=trace_correlation_id,
            status="completed",
            success_status="success" if summary["success"] else "failed",
            created_at=created,
            updated_at=_utc_now_iso(),
            runtime_kind=RuntimeKind.ENVIRONMENT,
            task=TaskDefinition(
                task_id=entry.task_id,
                task_name=f"DungeonGrid {entry.quest_id} {entry.player_mode}",
                task_family="dungeongrid",
                benchmark="dungeongrid",
                version=DUNGEONGRID_VERSION,
            ),
            task_instance=TaskInstance(
                task_instance_id=entry.task_instance_id,
                task_id=entry.task_id,
                split=entry.split,
                seed=entry.seed,
                input_payload=entry.input_payload(),
                tags=entry.tags(),
            ),
            actors=actors,
            trajectory=Trajectory(turns=turns, events=events, metadata={"transcript": transcript}),
            outcome=Outcome(
                reward=float(summary.get("total_reward", 0.0)),
                passed=bool(summary["success"]),
                details=metrics,
            ),
            checkpoint=checkpoint,
            parent_rollout_id=parent_rollout_id,
            parent_checkpoint_id=parent_checkpoint_id,
            summary=summary,
            usage={"env_steps": previous_turn_count + len(turns), "model_calls": 0},
            artifacts=[
                ArtifactDescriptor(
                    artifact_id=f"{rollout_id}_transcript",
                    kind="transcript",
                    media_type="application/json",
                    metadata=transcript,
                )
            ],
            state=StateSnapshot(
                state_id=f"{rollout_id}_state",
                values=env.public_state_json(),
                created_at=_utc_now_iso(),
                authoritative=True,
                metadata={"cell_key": summary["cell_key"]},
            ),
            metadata={
                "env_config": dict(config),
                "trial_id": trial_id or "",
                "agent_state": agent_snapshot,
                "rollout_state": rollout_snapshot,
            },
        )
        return execution

    def _store_checkpoint(
        self,
        *,
        rollout_id: str,
        env: DungeonGridEnvironment,
        config: dict[str, Any],
        agent_state: dict[str, Any] | None,
        rollout_state: dict[str, Any] | None,
        checkpoint_id: str | None,
        label: str | None,
        labels: list[str],
        actor_ids: list[str],
        metadata: dict[str, Any],
        annotations: dict[str, Any],
    ) -> CheckpointDescriptor:
        cid = checkpoint_id or f"dungeongrid_ckpt_{uuid.uuid4().hex[:10]}"
        encoded = _dump_checkpoint_payload(
            env,
            config,
            agent_state=agent_state,
            rollout_state=rollout_state,
        )
        self._checkpoint_data[cid] = encoded
        checkpoint_kind = (
            "agent_environment_snapshot"
            if agent_state or rollout_state
            else "environment_snapshot"
        )
        descriptor = CheckpointDescriptor(
            checkpoint_id=cid,
            rollout_id=rollout_id,
            checkpoint_uri=f"dungeongrid://checkpoints/{cid}",
            created_at=_utc_now_iso(),
            checkpoint_version=CHECKPOINT_VERSION,
            restore_eligible=True,
            label=label,
            labels=list(dict.fromkeys([item for item in labels if item])),
            source="dungeongrid_container",
            actor_ids=actor_ids,
            metadata={
                **metadata,
                "checkpoint_data_base64": encoded,
                "checkpoint_kind": checkpoint_kind,
                "agent_env_checkpoint_version": AGENT_ENV_CHECKPOINT_VERSION,
            },
            annotations=annotations,
            branchable=True,
            checkpoint_semantics=CheckpointSemantics.TRUE_ENVIRONMENT_SNAPSHOT,
            restore_semantics="true_environment_snapshot",
            true_environment_snapshot=True,
        )
        self._checkpoints[cid] = descriptor
        if self._store is not None:
            self._store.save_checkpoint(descriptor)
        return descriptor

    def _checkpoint_data_from_ref(self, checkpoint_ref: Mapping[str, Any] | None) -> str | None:
        if not checkpoint_ref:
            return None
        metadata = checkpoint_ref.get("metadata")
        if isinstance(metadata, Mapping):
            data = metadata.get("checkpoint_data_base64")
            if isinstance(data, str) and data:
                return data
        data = checkpoint_ref.get("checkpoint_data_base64")
        if isinstance(data, str) and data:
            return data
        return None

    def _checkpoint_data_for_id(self, checkpoint_id: str) -> str | None:
        data = self._checkpoint_data.get(checkpoint_id)
        if data is not None or self._store is None or not checkpoint_id:
            return data
        loaded = self._store.load_checkpoint(checkpoint_id)
        if loaded is None:
            return None
        descriptor, data = loaded
        self._checkpoints[checkpoint_id] = descriptor
        if data:
            self._checkpoint_data[checkpoint_id] = data
        return data or None

    def _cell_key(self, env: DungeonGridEnvironment) -> str:
        state = env.state
        rooms = tuple(sorted(room["id"] for room in env._visible_rooms("party")))
        achievements = tuple(sorted(state.achievements_unlocked))
        positions = tuple(
            (hero_id, hero.pos, hero.hp) for hero_id, hero in sorted(state.heroes.items())
        )
        objective = state.objective.carrier or ("map" if state.objective.pos else "missing")
        return repr(
            (state.quest_id, state.round, state.phase, rooms, achievements, positions, objective)
        )


def _coerce_int(value: Any) -> int | None:
    try:
        if value is None or str(value).strip() == "":
            return None
        return int(value)
    except (TypeError, ValueError):
        return None


def _max_steps(request: Mapping[str, Any], *, default: int) -> int:
    for source_key in ("terminator", "long_horizon", "params"):
        source = request.get(source_key)
        if isinstance(source, Mapping):
            value = _coerce_int(source.get("max_steps") or source.get("segment_steps"))
            if value:
                return value
    return default


def _policy_kind(request: Mapping[str, Any]) -> str:
    policy = request.get("policy")
    if isinstance(policy, Mapping):
        config = policy.get("config") if isinstance(policy.get("config"), Mapping) else policy
        return str(config.get("kind") or "achievement_scout")
    return "achievement_scout"


def _make_policy(policy_kind: str):
    return AchievementScoutPolicy() if policy_kind == "achievement_scout" else GreedyHeroPolicy()


def _snapshot_policy_state(policy: Any) -> dict[str, Any]:
    snapshot_state = getattr(policy, "snapshot_state", None)
    if callable(snapshot_state):
        value = snapshot_state()
        return dict(value) if isinstance(value, Mapping) else {}
    return {}
