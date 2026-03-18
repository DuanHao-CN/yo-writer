import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DEV_USER_ID
from app.core.database import get_db
from app.schemas.conversation import (
    ConversationCreate,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationResponse,
    MessageCreate,
    MessageResponse,
)
from app.services import conversation_service

router = APIRouter(prefix="/api/v1/conversations", tags=["conversations"])


@router.post("/", response_model=ConversationResponse, status_code=201)
async def create_conversation(
    data: ConversationCreate, db: AsyncSession = Depends(get_db)
) -> ConversationResponse:
    conv = await conversation_service.create_conversation(db, DEV_USER_ID, data)
    return ConversationResponse.model_validate(conv)


@router.get("/", response_model=ConversationListResponse)
async def list_conversations(
    agent_id: uuid.UUID | None = None,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> ConversationListResponse:
    items, total = await conversation_service.list_conversations(
        db, agent_id, offset, limit
    )
    return ConversationListResponse(
        items=[ConversationResponse.model_validate(c) for c in items],
        total=total,
    )


@router.get("/{conversation_id}", response_model=ConversationDetailResponse)
async def get_conversation(
    conversation_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> ConversationDetailResponse:
    conv = await conversation_service.get_conversation(db, conversation_id)
    return ConversationDetailResponse.model_validate(conv)


@router.delete("/{conversation_id}", status_code=204)
async def delete_conversation(
    conversation_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> None:
    await conversation_service.delete_conversation(db, conversation_id)


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=201,
)
async def send_message(
    conversation_id: uuid.UUID,
    data: MessageCreate,
    db: AsyncSession = Depends(get_db),
) -> MessageResponse:
    message = await conversation_service.add_message(db, conversation_id, data)
    return MessageResponse.model_validate(message)


@router.get(
    "/{conversation_id}/messages",
    response_model=list[MessageResponse],
)
async def get_messages(
    conversation_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> list[MessageResponse]:
    messages = await conversation_service.list_messages(db, conversation_id)
    return [MessageResponse.model_validate(m) for m in messages]
