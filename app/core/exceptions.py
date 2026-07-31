from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
import logging

logger = logging.getLogger("api_gateway")


def error_response(code: int, message: str) -> JSONResponse:
    return JSONResponse(
        status_code=code,
        content={
            "success": False,
            "error": {
                "code": code,
                "message": message,
            },
        },
    )


async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    return error_response(exc.status_code, exc.detail)


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    
    first_error = exc.errors()[0]
    field = ".".join(str(loc) for loc in first_error["loc"] if loc != "body")
    message = f"Invalid input for '{field}': {first_error['msg']}"
    return error_response(status.HTTP_422_UNPROCESSABLE_ENTITY, message)


async def unhandled_exception_handler(request: Request, exc: Exception):
    
    logger.exception("Unhandled exception occurred")
    
    return error_response(
        status.HTTP_500_INTERNAL_SERVER_ERROR,
        "An unexpected error occurred. Please try again later.",
    )