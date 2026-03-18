import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class ConversationCreate(BaseModel):
    agent_id: uuid.UUID
    title: str | None = None


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    agent_id: uuid.UUID
    user_id: uuid.UUID | None
    title: str | None
    created_at: datetime
    updated_at: datetime


class ConversationListResponse(BaseModel):
    items: list[ConversationResponse]
    total: int


class MessageCreate(BaseModel):
    role: str = Field(default="user", pattern="^(user|system)$")
    content: str = Field(min_length=1)


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str | None
    tool_calls: dict | None
    tool_call_id: str | None
    tokens_input: int | None
    tokens_output: int | None
    created_at: datetime


class ConversationDetailResponse(ConversationResponse):
    messages: list[MessageResponse] = []


class RunAgentRequest(BaseModel):
    messages: list[MessageCreate] = Field(min_length=1)
    stream: bool = False


class AgentRunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    conversation_id: uuid.UUID | None
    agent_id: uuid.UUID
    agent_version: int | None
    status: str
    total_tokens: int
    total_cost_usd: float
    duration_ms: int | None
    error: str | None
    trace_id: str | None
    started_at: datetime
    completed_at: datetime | None
