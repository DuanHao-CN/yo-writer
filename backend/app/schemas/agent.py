import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ModelConfig(BaseModel):
    provider: str = "openai"
    model_id: str = "gpt-5.4"
    temperature: float = Field(default=0.7, ge=0, le=2)
    max_tokens: int = Field(default=4096, ge=1, le=128000)


class GraphConfig(BaseModel):
    type: str = "react"
    max_iterations: int = Field(default=10, ge=1, le=100)


class HITLConfig(BaseModel):
    require_approval: list[str] = Field(default_factory=list)
    require_review: list[str] = Field(default_factory=list)


class AgentConfig(BaseModel):
    model: ModelConfig = Field(default_factory=ModelConfig)
    system_prompt: str = "You are a helpful assistant."
    graph: GraphConfig = Field(default_factory=GraphConfig)
    hitl: HITLConfig | None = None


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    description: str | None = None
    icon: str | None = None
    config: AgentConfig


class AgentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    description: str | None = None
    icon: str | None = None
    status: str | None = None
    config: AgentConfig | None = None


class AgentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    workspace_id: uuid.UUID
    name: str
    slug: str
    description: str | None
    icon: str | None
    status: str
    visibility: str
    current_version: int
    config: dict
    created_at: datetime
    updated_at: datetime


class AgentListResponse(BaseModel):
    items: list[AgentResponse]
    total: int
