import json
from importlib import resources

import pytest

from dungeongrid import (
    DeterministicWardenPolicy,
    DungeonGridEnvironment,
    WardenReActAdapter,
    make_dungeongrid_env_from_name,
)

QUEST_IDS = DungeonGridEnvironment().grid.available_quests()


@pytest.mark.parametrize("quest_id", QUEST_IDS)
def test_all_packaged_quests_reset(quest_id: str) -> None:
    env = DungeonGridEnvironment()

    obs = env.reset(quest_id=quest_id, num_heroes=1, seed=123)

    assert obs.agent_id
    assert obs.text
    assert env.private_state_json()["quest_id"] == quest_id


@pytest.mark.parametrize("quest_id", QUEST_IDS)
def test_all_packaged_quests_reset_classic_dynamic(quest_id: str) -> None:
    env = DungeonGridEnvironment()

    obs = env.reset(quest_id=quest_id, num_heroes=1, seed=123, ruleset="classic_dynamic")

    assert obs.agent_id
    assert obs.symbolic["ruleset_enabled"] is True


def test_invalid_action_is_reported_not_crashing() -> None:
    env = DungeonGridEnvironment()
    env.reset(quest_id="lantern_crypt", num_heroes=1, seed=123)

    step = env.step({"type": "definitely_not_a_real_action"})

    assert step.info.get("invalid") is True
    assert isinstance(step.reward, int | float)


def test_seeded_rollout_is_deterministic() -> None:
    def rollout() -> str:
        env = DungeonGridEnvironment()
        env.reset(quest_id="lantern_crypt", num_heroes=1, seed=7)

        for _ in range(5):
            step = env.step({"type": "end_turn"})
            if step.done:
                break

        return json.dumps(env.export_trace(), sort_keys=True, default=str)

    assert rollout() == rollout()


def test_public_state_redacts_private_information() -> None:
    env = DungeonGridEnvironment()
    env.reset(quest_id="lantern_crypt", num_heroes=1, seed=123, ruleset="classic_dynamic")

    public = env.public_state_json()
    private = env.private_state_json()

    assert "legal_actions" not in public
    assert public["dread"] is None
    assert isinstance(private["dread"], int)
    assert all(chest.get("contents") is None for chest in public["chests"].values())
    assert all(item.get("search_effects") is None for item in public["furniture"].values())


def test_factory_uses_stable_environment_names() -> None:
    env = make_dungeongrid_env_from_name("DungeonGrid-v0")
    assert isinstance(env, DungeonGridEnvironment)

    with pytest.raises(ValueError):
        make_dungeongrid_env_from_name("UnknownDungeonGrid-v0")


def test_packaged_dungeon_json_resources_exist() -> None:
    dungeon_root = resources.files("dungeongrid.dungeons")
    for quest_id in QUEST_IDS:
        assert dungeon_root.joinpath(quest_id, "quest.json").is_file()


def test_warden_observation_and_adapter_are_bounded() -> None:
    env = DungeonGridEnvironment()
    env.reset(quest_id="magistrate_gold", num_heroes=2, seed=1, ruleset="classic_dynamic")
    env.state.phase = "warden"
    env.state.dread = 2

    observation = env.observe_warden()

    assert observation["agent_id"] == "warden"
    assert observation["dread"] == 2
    assert observation["legal_actions"]
    assert "marl_axis" in observation

    adapter = WardenReActAdapter(lambda _obs: {"type": "move", "direction": "north"})
    action = adapter.act(observation)

    assert action["type"] in {candidate["type"] for candidate in observation["legal_actions"]}
    assert action["warden_policy"].endswith(":fallback")


def test_deterministic_warden_trace_includes_reasoning() -> None:
    env = DungeonGridEnvironment()
    env.reset(quest_id="magistrate_gold", num_heroes=2, seed=1, ruleset="classic_dynamic")
    env.state.phase = "warden"
    env.state.dread = 1

    action = DeterministicWardenPolicy().act(env.observe_warden())
    env.step(action, agent_id="warden")
    transcript = env.export_transcript()
    warden_turn = next(
        turn
        for turn in transcript["turns"]
        if turn.get("agent_id") == "warden" and turn.get("warden_policy")
    )

    assert warden_turn["warden_policy"] == "deterministic_warden"
    assert warden_turn["warden_intent"]
    assert warden_turn["warden_fairness_check"]


def test_classic_dynamic_role_requirements_are_hard_but_default_warns() -> None:
    env = DungeonGridEnvironment()

    env.reset(quest_id="low_shrine_locks", num_heroes=1, seed=1)
    assert any("Role warning" in event for event in env.state.event_log)

    with pytest.raises(ValueError, match="requires roles"):
        env.reset(
            quest_id="low_shrine_locks",
            num_heroes=1,
            seed=1,
            ruleset="classic_dynamic",
            hero_roles=["barbarian"],
        )


def test_specialist_action_rejects_wrong_role() -> None:
    env = DungeonGridEnvironment()
    env.reset(
        quest_id="low_shrine_locks",
        num_heroes=2,
        seed=1,
        ruleset="classic_dynamic",
        hero_roles=["dwarf", "elf"],
    )
    env.state.turn_index = 1
    elf = env.state.heroes["hero_2"]
    trap = next(iter(env.state.traps.values()))
    trap.pos = (elf.pos[0] + 1, elf.pos[1])
    trap.revealed = True
    trap.armed = True

    step = env.step({"type": "disarm", "target": trap.id}, agent_id="hero_2")

    assert step.info["invalid"] is True
    assert step.info["invalid_reason"] == "wrong_role"
