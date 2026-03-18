from app.runtime.engine import AgentRuntime


def test_register_agent_stores_graph_and_config(monkeypatch) -> None:
    runtime = AgentRuntime()
    sentinel_checkpointer = object()
    compiled_graph = object()
    received_checkpointer = None

    class FakeGraph:
        def compile(self, *, checkpointer: object) -> object:
            nonlocal received_checkpointer
            received_checkpointer = checkpointer
            return compiled_graph

    monkeypatch.setattr(
        "app.runtime.engine.get_persistent_checkpointer",
        lambda: sentinel_checkpointer,
    )
    monkeypatch.setattr("app.runtime.engine.build_react_graph", lambda: FakeGraph())

    agent_config = {
        "system_prompt": "Use the saved prompt.",
        "model": {"model_id": "gpt-test"},
    }

    runtime.register_agent("demo-agent", agent_config)

    assert received_checkpointer is sentinel_checkpointer
    assert runtime.get_graph("demo-agent") is compiled_graph
    assert runtime.langgraph_configs["demo-agent"] == {
        "configurable": {"agent_config": agent_config}
    }


def test_get_langgraph_config_returns_defensive_copy() -> None:
    runtime = AgentRuntime()
    runtime.langgraph_configs["demo-agent"] = {
        "configurable": {"agent_config": {"system_prompt": "Original"}}
    }

    config = runtime.get_langgraph_config("demo-agent")
    assert config is not None
    config["configurable"]["agent_config"]["system_prompt"] = "Mutated"

    assert (
        runtime.langgraph_configs["demo-agent"]["configurable"]["agent_config"][
            "system_prompt"
        ]
        == "Original"
    )


def test_unregister_agent_removes_from_registry(monkeypatch) -> None:
    runtime = AgentRuntime()
    monkeypatch.setattr(
        "app.runtime.engine.get_persistent_checkpointer", lambda: object()
    )

    class FakeGraph:
        def compile(self, *, checkpointer):
            return object()

    monkeypatch.setattr("app.runtime.engine.build_react_graph", lambda: FakeGraph())

    runtime.register_agent("to-remove", {"system_prompt": "test"})
    assert "to-remove" in runtime.graphs

    runtime.unregister_agent("to-remove")
    assert "to-remove" not in runtime.graphs
    assert "to-remove" not in runtime.langgraph_configs


def test_clear_registered_agents(monkeypatch) -> None:
    runtime = AgentRuntime()
    runtime.graphs["a"] = object()
    runtime.langgraph_configs["a"] = {}

    runtime.clear_registered_agents()
    assert len(runtime.graphs) == 0
    assert len(runtime.langgraph_configs) == 0
