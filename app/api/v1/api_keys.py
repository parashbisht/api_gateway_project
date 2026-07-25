from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.db.session import get_db
from app.models.api_key import APIKey
from app.models.user import User
from app.schemas.api_key import APIKeyCreate, APIKeyCreated, APIKeyOut
from app.core.security import generate_api_key
from app.deps import get_current_user

router = APIRouter(prefix="/api/v1/api-keys", tags=["api-keys"])


@router.post("", response_model=APIKeyCreated, status_code=status.HTTP_201_CREATED)
def create_api_key(
    payload: APIKeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    raw_key, prefix, hashed_key = generate_api_key()

    api_key = APIKey(
        name=payload.name,
        prefix=prefix,
        hashed_key=hashed_key,
        user_id=current_user.id,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)

   
    return APIKeyCreated(
        id=api_key.id,
        name=api_key.name,
        raw_key=raw_key,
        prefix=api_key.prefix,
        created_at=api_key.created_at,
    )


@router.get("", response_model=list[APIKeyOut])
def list_api_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return db.query(APIKey).filter(APIKey.user_id == current_user.id).all()


@router.patch("/{key_id}/disable", response_model=APIKeyOut)
def disable_api_key(
    key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id, APIKey.user_id == current_user.id
    ).first()

    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    api_key.active = False
    api_key.revoked_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(api_key)
    return api_key


@router.delete("/{key_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_api_key(
    key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    api_key = db.query(APIKey).filter(
        APIKey.id == key_id, APIKey.user_id == current_user.id
    ).first()

    if not api_key:
        raise HTTPException(status_code=404, detail="API key not found")

    
    api_key.active = False
    api_key.revoked_at = datetime.now(timezone.utc)
    db.commit()
    return None