import re
import unicodedata

from app.schemas.agent import StockQueryArguments, ToolCall


class UnsupportedQuestionError(ValueError):
    pass


def parse_question(question: str) -> ToolCall:
    normalized = unicodedata.normalize("NFKD", question.lower())
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    match = re.search(r"estoque\s+(?:abaixo|menor)\s+(?:de|que)\s+(\d+)", normalized)
    if not match:
        raise UnsupportedQuestionError("question is not supported")
    return ToolCall(
        name="find_low_stock",
        arguments=StockQueryArguments(max_quantity=int(match.group(1))),
    )
