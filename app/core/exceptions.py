from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from app.core.logger import get_logger

logger = get_logger("api_gateway.errors")


def _get_request_id(request: Request) -> str | None:
    return getattr(request.state, "request_id", None)


def error_response(code: int, message: str, request_id: str | None) -> JSONResponse:
    return JSONResponse(
        status_code=code,
        content={
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id,
            },
        },
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    request_id = _get_request_id(request)
    response = error_response(exc.status_code, exc.detail, request_id)
    if exc.headers:
        for key, value in exc.headers.items():
            response.headers[key] = value
    return response

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    first_error = exc.errors()[0]
    field = ".".join(str(loc) for loc in first_error["loc"] if loc != "body")
    message = f"Invalid input for '{field}': {first_error['msg']}"
    return error_response(
        status.HTTP_422_UNPROCESSABLE_ENTITY, message, _get_request_id(request)
    )


async def unhandled_exception_handler(request: Request, exc: Exception):
    request_id = _get_request_id(request)
    logger.error(
        "Unhandled exception occurred",
        extra={"request_id": request_id, "error": str(exc)},
    )
    return error_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "An unexpected error occurred. Please try again later.",
        request_id,
    )

