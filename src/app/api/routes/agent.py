from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import current_user
from app.db.session import get_session
from app.models import User
from app.schemas.agent import AgentQuestion, AgentResult
from app.services.agent_service import UnsupportedQuestionError, parse_question
from app.services.agent_tool_service import execute_tool_call

router = APIRouter(prefix="/api/v1/agent", tags=["agent"])


@router.post("/query", response_model=AgentResult)
async def query_agent(
    payload: AgentQuestion,
    session: AsyncSession = Depends(get_session),
    _: User = Depends(current_user),
) -> AgentResult:
    try:
        tool_call = parse_question(payload.question)
    except UnsupportedQuestionError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    products = await execute_tool_call(session, tool_call)
    return AgentResult(
        tool_call=tool_call,
        result=[
            {"id": product.id, "name": product.name, "stock_quantity": product.stock_quantity}
            for product in products
        ],
    )
