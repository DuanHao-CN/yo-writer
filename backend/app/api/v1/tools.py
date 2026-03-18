import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.constants import DEV_WORKSPACE_ID
from app.core.database import get_db
from app.schemas.tool import (
    ToolCreate,
    ToolListResponse,
    ToolResponse,
    ToolTestRequest,
    ToolTestResponse,
    ToolUpdate,
)
from app.services import tool_service

router = APIRouter(prefix="/api/v1/tools", tags=["tools"])


@router.post("/", response_model=ToolResponse, status_code=201)
async def create_tool(
    data: ToolCreate, db: AsyncSession = Depends(get_db)
) -> ToolResponse:
    tool = await tool_service.create_tool(db, DEV_WORKSPACE_ID, data)
    return ToolResponse.model_validate(tool)


@router.get("/", response_model=ToolListResponse)
async def list_tools(
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> ToolListResponse:
    items, total = await tool_service.list_tools(db, DEV_WORKSPACE_ID, offset, limit)
    return ToolListResponse(
        items=[ToolResponse.model_validate(t) for t in items],
        total=total,
    )


@router.get("/{tool_id}", response_model=ToolResponse)
async def get_tool(
    tool_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> ToolResponse:
    tool = await tool_service.get_tool(db, tool_id)
    return ToolResponse.model_validate(tool)


@router.patch("/{tool_id}", response_model=ToolResponse)
async def update_tool(
    tool_id: uuid.UUID,
    data: ToolUpdate,
    db: AsyncSession = Depends(get_db),
) -> ToolResponse:
    tool = await tool_service.update_tool(db, tool_id, data)
    return ToolResponse.model_validate(tool)


@router.delete("/{tool_id}", status_code=204)
async def delete_tool(
    tool_id: uuid.UUID, db: AsyncSession = Depends(get_db)
) -> None:
    await tool_service.delete_tool(db, tool_id)


@router.post("/{tool_id}/test", response_model=ToolTestResponse)
async def test_tool(
    tool_id: uuid.UUID,
    data: ToolTestRequest,
    db: AsyncSession = Depends(get_db),
) -> ToolTestResponse:
    # Verify tool exists
    await tool_service.get_tool(db, tool_id)
    result = await tool_service.test_tool(data.tool_name, data.arguments)
    return ToolTestResponse(**result)
