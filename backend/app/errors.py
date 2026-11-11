"""Error handling: one error shape, generic messages, privacy-safe logs.

Responses always look like {"error": {"code", "message", "retryable"}} and never
contain stack traces, provider errors, prompts or request ids. Unexpected
exceptions are logged with their class and stack frames but not their message,
because messages (e.g. database errors) can echo stored values such as symptom text.
They are caught in a middleware rather than an `Exception` handler: Starlette
re-raises after such a handler and the server would then log the full traceback,
message included.
"""

import logging
import traceback
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.schemas import ErrorResponse

log = logging.getLogger(__name__)

HTTP_ERROR_CODES = {
    401: "unauthorized",
    404: "not_found",
    422: "validation_error",
    429: "rate_limited",
}
HTTP_ERROR_MESSAGES = {404: "We couldn't find what you were looking for."}
GENERIC_MESSAGE = "Something went wrong. Please try again."


class ApiError(Exception):
    def __init__(self, status_code: int, code: str, message: str, retryable: bool = False) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message
        self.retryable = retryable


def error_response(
    status_code: int, code: str, message: str, retryable: bool = False
) -> JSONResponse:
    body = {"error": {"code": code, "message": message, "retryable": retryable}}
    return JSONResponse(status_code=status_code, content=body)


async def api_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, ApiError)
    return error_response(exc.status_code, exc.code, exc.message, exc.retryable)


async def validation_error_handler(request: Request, exc: Exception) -> JSONResponse:
    return error_response(422, "validation_error", "Please check your input and try again.")


async def http_error_handler(request: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, HTTPException)
    code = HTTP_ERROR_CODES.get(exc.status_code, "internal_error")
    return error_response(
        exc.status_code, code, HTTP_ERROR_MESSAGES.get(exc.status_code, GENERIC_MESSAGE)
    )


async def catch_unhandled_errors(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    try:
        return await call_next(request)
    except Exception as exc:
        frames = "".join(traceback.format_tb(exc.__traceback__))
        log.error(
            "unhandled %s on %s %s\n%s",
            type(exc).__name__,
            request.method,
            request.url.path,
            frames,
        )
        return error_response(500, "internal_error", GENERIC_MESSAGE, retryable=True)


def error_responses(*status_codes: int) -> dict[int | str, dict[str, object]]:
    """OpenAPI `responses=` entries documenting the common error shape."""
    return {code: {"model": ErrorResponse} for code in status_codes}


EXCEPTION_HANDLERS = {
    ApiError: api_error_handler,
    RequestValidationError: validation_error_handler,
    HTTPException: http_error_handler,
}


def install_error_handling(app: FastAPI) -> None:
    """Call before adding other middleware, so that e.g. CORS headers are added to 500s too."""
    for exception_class, handler in EXCEPTION_HANDLERS.items():
        app.add_exception_handler(exception_class, handler)
    app.middleware("http")(catch_unhandled_errors)


def configure_logging(level: str = "INFO") -> None:
    logging.basicConfig(level=level, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
