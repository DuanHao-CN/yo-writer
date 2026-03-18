import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ToolCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    type: str = Field(default="builtin", max_length=30)
    mcp_uri: str | None = None
    schema_json: dict = Field(default_factory=dict)  # noqa: Pydantic shadow warning
    config: dict = Field(default_factory=dict)


class ToolUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    type: str | None = Field(default=None, max_length=30)
    mcp_uri: str | None = None
    schema_json: dict | None = None
    config: dict | None = None
    status: str | None = None


class ToolResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    slug: str
    description: str | None
    type: str
    mcp_uri: str | None
    config: dict
    schema_json: dict
    status: str
    created_at: datetime
    updated_at: datetime


class ToolListResponse(BaseModel):
    items: list[ToolResponse]
    total: int


class AgentToolBind(BaseModel):
    tool_id: uuid.UUID
    config_override: dict = Field(default_factory=dict)


class AgentToolResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    agent_id: uuid.UUID
    tool_id: uuid.UUID
    config_override: dict
    created_at: datetime
    tool: ToolResponse


class ToolTestRequest(BaseModel):
    tool_name: str
    arguments: dict = Field(default_factory=dict)


class ToolTestResponse(BaseModel):
    result: str
    duration_ms: int
    status: str
