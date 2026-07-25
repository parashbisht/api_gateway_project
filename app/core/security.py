from datetime import datetime, timedelta, timezone
import bcrypt
from jose import jwt, JWTError

from app.core.config import settings


def hash_password(password: str) -> str:
    pwd_bytes = password.encode("utf-8")
    hashed = bcrypt.hashpw(pwd_bytes, bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode("utf-8"),
        hashed_password.encode("utf-8"),
    )


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict | None:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError:
        return None


import secrets

def generate_api_key() -> tuple[str, str, str]:
    raw_secret = secrets.token_urlsafe(32)          
    raw_key = f"sk_live_{raw_secret}"
    prefix = raw_key[:14]                            

    hashed_key = bcrypt.hashpw(raw_key.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    return raw_key, prefix, hashed_key


def verify_api_key(raw_key: str, hashed_key: str) -> bool:
    return bcrypt.checkpw(raw_key.encode("utf-8"), hashed_key.encode("utf-8"))