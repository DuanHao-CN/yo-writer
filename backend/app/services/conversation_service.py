import uuid
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.errors import APIError
from app.models.agent import Conversation, Message
from app.schemas.conversation import ConversationCreate, MessageCreate
from app.services import agent_service


def _extract_assistant_content(result: dict[str, Any]) -> str | None:
    for message in reversed(result.get("messages", [])):
        if message.get("role") != "assistant":
            continue

        content = message.get("content")
        if content is None:
            return None
        if isinstance(content, str):
            return content
        return str(content)

    return None


async def create_conversation(
    db: AsyncSession, user_id: str, data: ConversationCreate
) -> Conversation:
    # Verify agent exists
    await agent_service.get_agent(db, data.agent_id)

    conversation = Conversation(
        agent_id=data.agent_id,
        user_id=uuid.UUID(user_id),
        title=data.title,
    )
    db.add(conversation)
    await db.commit()
    await db.refresh(conversation)
    return conversation


async def list_conversations(
    db: AsyncSession,
    agent_id: uuid.UUID | None = None,
    offset: int = 0,
    limit: int = 20,
) -> tuple[list[Conversation], int]:
    query = select(Conversation)
    count_query = select(func.count()).select_from(Conversation)

    if agent_id:
        query = query.where(Conversation.agent_id == agent_id)
        count_query = count_query.where(Conversation.agent_id == agent_id)

    total = await db.scalar(count_query)

    result = await db.execute(
        query.order_by(Conversation.updated_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all()), total or 0


async def get_conversation(
    db: AsyncSession, conversation_id: uuid.UUID
) -> Conversation:
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.messages))
        .where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    if not conversation:
        raise APIError(
            code="CONVERSATION_NOT_FOUND",
            message="Conversation not found",
            status_code=404,
        )
    return conversation


async def delete_conversation(
    db: AsyncSession, conversation_id: uuid.UUID
) -> None:
    conversation = await get_conversation(db, conversation_id)
    await db.delete(conversation)
    await db.commit()


async def add_message(
    db: AsyncSession, conversation_id: uuid.UUID, data: MessageCreate
) -> Message:
    conversation = await get_conversation(db, conversation_id)

    message = Message(
        conversation_id=conversation_id,
        role=data.role,
        content=data.content,
    )
    db.add(message)
    conversation.updated_at = func.now()
    await db.commit()
    await db.refresh(message)

    agent = await agent_service.get_agent(db, conversation.agent_id)

    from app.runtime.engine import agent_runtime

    result = await agent_runtime.run(
        agent=agent,
        messages=[{"role": data.role, "content": data.content}],
        thread_id=str(conversation.id),
        conversation_id=conversation.id,
    )

    assistant_content = _extract_assistant_content(result)
    if assistant_content is not None:
        assistant_message = Message(
            conversation_id=conversation_id,
            role="assistant",
            content=assistant_content,
        )
        db.add(assistant_message)
        conversation.updated_at = func.now()
        await db.commit()

    return message


async def list_messages(
    db: AsyncSession, conversation_id: uuid.UUID
) -> list[Message]:
    # Verify conversation exists
    await get_conversation(db, conversation_id)

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.created_at)
    )
    return list(result.scalars().all())
