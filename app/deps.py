from fastapi import Depends, HTTPException, status, Header
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from typing import Optional

from app.db.session import get_db
from app.core.security import decode_access_token, verify_api_key
from app.models.user import User
from app.models.api_key import APIKey
from app.core.rate_limiter import check_rate_limit

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login", auto_error=False)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise credentials_exception

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None:
        raise credentials_exception

    return user


def get_user_from_api_key(
    x_api_key: Optional[str] = Header(default=None),
    db: Session = Depends(get_db),
) -> Optional[User]:
    if x_api_key is None:
        return None

    
    prefix = x_api_key[:14]
    candidate_keys = db.query(APIKey).filter(
        APIKey.prefix == prefix,
        APIKey.active == True,
    ).all()

    for key_row in candidate_keys:
        if verify_api_key(x_api_key, key_row.hashed_key):
            return key_row.user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or inactive API key",
    )


def get_current_identity(
    x_api_key: Optional[str] = Header(default=None),
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
  
    if x_api_key is not None:
        user = get_user_from_api_key(x_api_key=x_api_key, db=db)
        if user:
            return user

    if token is not None:
        return get_current_user(token=token, db=db)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Not authenticated: provide a valid Bearer token or X-API-Key header",

)

def rate_limited_identity(
    current_identity: User = Depends(get_current_identity),
) -> User:
    check_rate_limit(user_id=current_identity.id, plan=current_identity.plan)
    return current_identity
    