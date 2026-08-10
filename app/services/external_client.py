import httpx
from fastapi import HTTPException, status
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger("api_gateway.downstream")


async def call_downstream_service(url: str, request_id: str | None = None) -> dict:
    """
    Makes an outbound call to a downstream/external service with an
    explicit, configurable timeout. Never hangs indefinitely.
    """
    timeout = settings.DOWNSTREAM_TIMEOUT_SECONDS

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.get(url)
            response.raise_for_status()
            return response.json()

    except httpx.TimeoutException:
        logger.error(
            "Downstream service timed out",
            extra={"request_id": request_id, "error": f"timeout after {timeout}s", "path": url},
        )
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=f"Downstream service did not respond within {timeout} seconds.",
        )

    except httpx.RequestError as e:
        logger.error(
            "Downstream service request failed",
            extra={"request_id": request_id, "error": str(e), "path": url},
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Downstream service is unavailable.",
        )