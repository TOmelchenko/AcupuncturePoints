"""The API's common error shape: {"error": {"code": "...", "message": "...", "retryable": ...}}.

Messages are generic and safe to show to users; details stay in the logs.
"""

from fastapi import Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.schemas import ErrorResponse


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


def error_responses(*status_codes: int) -> dict[int | str, dict[str, object]]:
    """OpenAPI `responses=` entries documenting the common error shape."""
    return {code: {"model": ErrorResponse} for code in status_codes}


EXCEPTION_HANDLERS = {ApiError: api_error_handler, RequestValidationError: validation_error_handler}
