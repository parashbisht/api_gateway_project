from pydantic import BaseModel


class PlanInfo(BaseModel):
    plan_id: str
    display_name: str
    requests_per_hour: int | None
    can_access_premium_analytics: bool


class PlanUpdate(BaseModel):
    plan: str  # "free" | "premium" | "enterprise"