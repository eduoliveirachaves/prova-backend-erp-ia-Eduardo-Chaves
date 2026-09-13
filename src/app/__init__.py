from app.api.main import app


def main() -> None:
    import uvicorn

    uvicorn.run("app.api.main:app", host="0.0.0.0", port=8000, reload=False)


__all__ = ["app", "main"]
