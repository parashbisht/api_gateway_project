from pydantic import BaseModel
from datetime import datetime


class ProductCreate(BaseModel):
    name: str
    price: float
    description: str | None = None


class ProductOut(BaseModel):
    id: int
    name: str
    price: float
    description: str | None
    created_at: datetime

    class Config:
        from_attributes = True