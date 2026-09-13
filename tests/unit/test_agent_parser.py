import pytest

from app.services.agent_service import (
    UnsupportedQuestionError,
    parse_question,
)


def test_parse_low_stock_question_into_structured_intent() -> None:
    result = parse_question("Quais produtos estão com estoque abaixo de 10 unidades?")

    assert result.name == "find_low_stock"
    assert result.arguments.max_quantity == 10


def test_parse_question_rejects_unknown_intent() -> None:
    with pytest.raises(UnsupportedQuestionError):
        parse_question("Crie um pedido para o cliente 42")
