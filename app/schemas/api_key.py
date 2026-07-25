from pydantic import BaseModel
from datetime import datetime


class APIKeyCreate(BaseModel):
    name: str


class APIKeyCreated(BaseModel):
    id: int
    name: str
    raw_key: str          
    prefix: str
    created_at: datetime

    class Config:
        from_attributes = True


class APIKeyOut(BaseModel):
    id: int
    name: str
    prefix: str
    active: bool
    created_at: datetime
    revoked_at: datetime | None

    class Config:
        from_attributes = True