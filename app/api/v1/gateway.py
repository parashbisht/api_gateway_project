from fastapi import APIRouter, Depends
from app.deps import rate_limited_identity
from app.models.user import User

router = APIRouter(prefix="/gateway", tags=["gateway"])


@router.get("/ping")
def gateway_ping(current_identity: User = Depends(rate_limited_identity)):
    return {
        "message": "Authenticated successfully",
        "user_id": current_identity.id,
        "email": current_identity.email,
        "plan": current_identity.plan,
    }


from fastapi import Request
from app.services.external_client import call_downstream_service

@router.get("/external-check")
async def external_check(request: Request, delay: int = 2):
    """
    Demonstrates downstream timeout handling by calling a public test
    endpoint that can be made to respond slowly on purpose.
    """
    request_id = getattr(request.state, "request_id", None)
    url = f"https://httpbin.org/delay/{delay}"
    result = await call_downstream_service(url, request_id=request_id)
    return {"message": "Downstream call succeeded", "delay_requested": delay}