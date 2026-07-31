from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.core.plans import PLAN_DETAILS
from app.schemas.plan import PlanInfo, PlanUpdate
from app.deps import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/v1", tags=["plans"])


@router.get("/plans", response_model=list[PlanInfo])
def list_plans():
    return [
        PlanInfo(plan_id=plan_id, **details)
        for plan_id, details in PLAN_DETAILS.items()
    ]


@router.get("/me/plan", response_model=PlanInfo)
def get_my_plan(current_user: User = Depends(get_current_user)):
    details = PLAN_DETAILS.get(current_user.plan)
    return PlanInfo(plan_id=current_user.plan, **details)


@router.patch("/me/plan", response_model=PlanInfo)
def update_my_plan(
    payload: PlanUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if payload.plan not in PLAN_DETAILS:
        raise HTTPException(status_code=400, detail="Invalid plan")

    current_user.plan = payload.plan
    db.commit()
    db.refresh(current_user)

    details = PLAN_DETAILS[current_user.plan]
    return PlanInfo(plan_id=current_user.plan, **details)