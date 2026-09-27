"""Every error body is {"detail": "<string>", "code": "<machine_code>"} so the frontend can always
render `detail` directly (FastAPI's default 422 body is a list of objects, which crashes React)."""
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str):
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_request: Request, exc: ApiError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message, "code": exc.code})

    @app.exception_handler(RequestValidationError)
    async def _validation_error(_request: Request, exc: RequestValidationError):
        errors = [
            {
                "field": ".".join(str(p) for p in e["loc"] if p not in ("body", "query", "path")),
                "message": e["msg"],
            }
            for e in exc.errors()
        ]
        first = errors[0] if errors else {"field": "", "message": "잘못된 요청입니다"}
        detail = f'{first["field"]}: {first["message"]}' if first["field"] else first["message"]
        return JSONResponse(
            status_code=422,
            content={"detail": detail, "code": "validation_error", "errors": errors},
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http_error(_request: Request, exc: StarletteHTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": str(exc.detail), "code": "http_error"},
            headers=getattr(exc, "headers", None),
        )
