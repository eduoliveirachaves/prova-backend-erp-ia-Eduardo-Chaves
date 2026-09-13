from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.schemas.product import ProductCreate


def test_product_create_accepts_valid_values() -> None:
    product = ProductCreate(name="Notebook", price=Decimal("1999.90"), stock_quantity=4)

    assert product.name == "Notebook"
    assert product.price == Decimal("1999.90")
    assert product.stock_quantity == 4


@pytest.mark.parametrize(
    "payload",
    [
        {"name": "", "price": 10, "stock_quantity": 1},
        {"name": "12345", "price": 10, "stock_quantity": 1},
        {"name": "Produto", "price": -1, "stock_quantity": 1},
        {"name": "Produto", "price": 10, "stock_quantity": -1},
    ],
)
def test_product_create_rejects_invalid_values(payload: dict[str, object]) -> None:
    with pytest.raises(ValidationError):
        ProductCreate.model_validate(payload)
