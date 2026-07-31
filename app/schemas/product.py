from pydantic import BaseModel, Field
from datetime import datetime


class ProductCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    price: float = Field(gt=0)  # must be strictly greater than 0
    description: str | None = Field(default=None, max_length=1000)


class ProductOut(BaseModel):
    id: int
    name: str
    price: float
    description: str | None
    created_at: datetime

    class Config:
        from_attributes = True