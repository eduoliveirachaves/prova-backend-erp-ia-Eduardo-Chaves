from pydantic import BaseModel


class SourceResult(BaseModel):
    status: str
    attempts: int
    data: dict[str, object] | None = None
    error: str | None = None


class DashboardResult(BaseModel):
    product_id: int
    stock: SourceResult
    customer: SourceResult
    financial: SourceResult
