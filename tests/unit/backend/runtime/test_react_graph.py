from app.runtime.graphs.react import _get_bound_tools


def _tool_names(tools: list[dict]) -> list[str]:
    names: list[str] = []
    for tool in tools:
        if tool.get("type") == "function":
            names.append(tool["function"]["name"])
        else:
            names.append(tool["name"])
    return names


def test_get_bound_tools_includes_frontend_actions_without_duplicates() -> None:
    frontend_tool = {
        "name": "render_chart",
        "description": "Render a chart",
        "parameters": {"type": "object", "properties": {"title": {"type": "string"}}},
    }
    duplicate_builtin_tool = {
        "name": "calculator",
        "description": "Duplicate builtin tool",
        "parameters": {"type": "object", "properties": {}},
    }

    # Use AgentState-compatible dict with tools and copilotkit fields
    state = {
        "messages": [],
        "tools": [frontend_tool, duplicate_builtin_tool],
        "copilotkit": {},
    }
    tools = _get_bound_tools(state)

    names = set(_tool_names(tools))
    assert "calculator" in names
    assert "render_chart" in names
    assert len(tools) == 2  # no duplicates


def test_get_bound_tools_returns_mock_tools_when_no_frontend_tools() -> None:
    state = {"messages": [], "tools": [], "copilotkit": {}}
    tools = _get_bound_tools(state)
    assert _tool_names(tools) == ["calculator"]
