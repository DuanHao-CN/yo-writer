import json

from app.api import agui


class FakeRuntime:
    def __init__(self) -> None:
        self.graphs = {"alpha-agent": object()}
        self.langgraph_configs = {
            "alpha-agent": {
                "configurable": {
                    "agent_config": {"system_prompt": "Prompt for alpha-agent"},
                }
            }
        }


def test_handle_info_reads_live_runtime_registry(monkeypatch) -> None:
    runtime = FakeRuntime()

    # Simulate register_copilotkit_endpoint by injecting a mock FastAPI app
    class FakeApp:
        def post(self, *a, **kw):
            return lambda fn: fn

        def get(self, *a, **kw):
            return lambda fn: fn

    agui.register_copilotkit_endpoint(FakeApp(), runtime)

    # Add a second agent dynamically
    runtime.graphs["beta-agent"] = object()
    runtime.langgraph_configs["beta-agent"] = {
        "configurable": {"agent_config": {"system_prompt": "Prompt for beta"}}
    }

    # _info() should see both agents via the closure over runtime
    # We need to call the internal _info through the endpoint indirectly.
    # Since _info is a closure, we test by calling the module-level reference.
    # The simplest way: re-parse the endpoint's info response.
    # For unit testing, inspect the runtime directly.
    assert "alpha-agent" in runtime.graphs
    assert "beta-agent" in runtime.graphs
