from pydantic import BaseModel
from fastapi import Query


class PaginationParams:
    def __init__(
        self,
        limit: int = Query(default=20, ge=1, le=100, description="Max items to return (1-100)"),
        offset: int = Query(default=0, ge=0, description="Number of items to skip"),
    ):
        self.limit = limit
        self.offset = offset


class PaginatedResponse(BaseModel):
    total: int
    limit: int
    offset: int
    items: list