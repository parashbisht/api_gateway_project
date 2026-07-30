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