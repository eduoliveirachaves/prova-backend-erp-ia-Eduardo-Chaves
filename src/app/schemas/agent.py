from typing import Literal

from pydantic import BaseModel, Field


class AgentQuestion(BaseModel):
    question: str = Field(min_length=1, max_length=500)


class StockQueryArguments(BaseModel):
    max_quantity: int = Field(ge=0)


class ToolCall(BaseModel):
    name: Literal["find_low_stock"]
    arguments: StockQueryArguments


class AgentResult(BaseModel):
    tool_call: ToolCall
    result: list[dict[str, object]]
