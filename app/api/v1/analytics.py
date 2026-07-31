from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, case
from datetime import datetime, timezone

from app.db.session import get_db
from app.models.request_log import RequestLog
from app.schemas.analytics import OverviewStats, EndpointStat, UserStat
from app.deps import get_current_user
from app.models.user import User
from fastapi import HTTPException
from app.core.plans import PLAN_DETAILS

router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])


@router.get("/overview", response_model=OverviewStats)
def get_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    total_requests = db.query(func.count(RequestLog.id)).scalar()

    today_start = datetime.now(timezone.utc).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    requests_today = db.query(func.count(RequestLog.id)).filter(
        RequestLog.timestamp >= today_start
    ).scalar()

    avg_response_time = db.query(func.avg(RequestLog.response_time_ms)).scalar()

    failed_requests = db.query(func.count(RequestLog.id)).filter(
        RequestLog.status_code >= 400
    ).scalar()

    success_rate = (
        ((total_requests - failed_requests) / total_requests * 100)
        if total_requests > 0 else 0.0
    )

    return OverviewStats(
        total_requests=total_requests or 0,
        requests_today=requests_today or 0,
        average_response_time_ms=round(avg_response_time or 0.0, 2),
        failed_requests=failed_requests or 0,
        success_rate_percent=round(success_rate, 2),
    )


@router.get("/top-endpoints", response_model=list[EndpointStat])
def get_top_endpoints(
    limit: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    results = (
        db.query(
            RequestLog.endpoint,
            func.count(RequestLog.id).label("request_count"),
        )
        .group_by(RequestLog.endpoint)
        .order_by(func.count(RequestLog.id).desc())
        .limit(limit)
        .all()
    )
    return [EndpointStat(endpoint=r.endpoint, request_count=r.request_count) for r in results]


@router.get("/top-users", response_model=list[UserStat])
def get_top_users(
    limit: int = 5,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    results = (
        db.query(
            RequestLog.user_id,
            func.count(RequestLog.id).label("request_count"),
        )
        .filter(RequestLog.user_id.isnot(None))
        .group_by(RequestLog.user_id)
        .order_by(func.count(RequestLog.id).desc())
        .limit(limit)
        .all()
    )
    return [UserStat(user_id=r.user_id, request_count=r.request_count) for r in results]


@router.get("/premium-insights")
def get_premium_insights(current_user: User = Depends(get_current_user)):
    plan_info = PLAN_DETAILS.get(current_user.plan)
    if not plan_info or not plan_info["can_access_premium_analytics"]:
        raise HTTPException(
            status_code=403,
            detail="This feature requires a Premium or Enterprise plan",
        )
    return {"message": "Here are your premium insights (simulated)."}