from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.deps import rate_limited_identity
from app.models.user import User
from app.schemas.user import UserOut

router = APIRouter()


@router.get("/users/me", response_model=UserOut)
def get_my_user(
    current_identity: User = Depends(rate_limited_identity),
):
    return current_identity