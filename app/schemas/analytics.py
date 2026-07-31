from pydantic import BaseModel


class OverviewStats(BaseModel):
    total_requests: int
    requests_today: int
    average_response_time_ms: float
    failed_requests: int
    success_rate_percent: float


class EndpointStat(BaseModel):
    endpoint: str
    request_count: int


class UserStat(BaseModel):
    user_id: int
    request_count: int