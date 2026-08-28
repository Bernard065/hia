"""Shared HTTP concerns: request tracing and stable error responses."""

from uuid import uuid4

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.error_codes import ERROR_CODE_BY_HTTP_STATUS, ErrorCode


def error_response(
    request: Request,
    status_code: int,
    message: str,
    field: str | None = None,
) -> JSONResponse:
    """Build the documented error envelope without exposing internals."""
    error = {
        "code": ERROR_CODE_BY_HTTP_STATUS.get(
            status_code,
            ErrorCode.INTERNAL_ERROR,
        ),
        "message": message,
        "request_id": request.state.request_id,
    }

    if field:
        error["field"] = field

    return JSONResponse(
        status_code=status_code,
        content={"error": error},
    )


def configure_api(app: FastAPI) -> None:
    """Install request tracing and common exception handling."""

    @app.middleware("http")
    async def add_request_id(request: Request, call_next):
        request.state.request_id = str(uuid4())

        response = await call_next(request)
        response.headers["X-Request-ID"] = request.state.request_id

        return response

    @app.exception_handler(HTTPException)
    async def handle_http_exception(
        request: Request,
        exc: HTTPException,
    ) -> JSONResponse:
        return error_response(
            request,
            exc.status_code,
            str(exc.detail),
        )

    @app.exception_handler(StarletteHTTPException)
    async def handle_starlette_http_exception(
        request: Request,
        exc: StarletteHTTPException,
    ) -> JSONResponse:
        return error_response(
            request,
            exc.status_code,
            str(exc.detail),
        )

    @app.exception_handler(RequestValidationError)
    async def handle_validation_error(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        first_error = exc.errors()[0]
        field = ".".join(
            str(part)
            for part in first_error["loc"]
            if part != "body"
        )

        return error_response(
            request,
            status.HTTP_400_BAD_REQUEST,
            first_error["msg"],
            field or None,
        )

    @app.exception_handler(Exception)
    async def handle_unexpected_error(
        request: Request,
        _exc: Exception,
    ) -> JSONResponse:
        """Return a safe error without exposing implementation details."""
        return error_response(
            request,
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "an unexpected error occurred",
        )
