from fastapi import APIRouter, BackgroundTasks, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.ai_campaign import AICampaign
from app.services.ai_worker import execute_ai_sdr_workflow
from app.deps import rate_limited_identity
from app.models.user import User

router = APIRouter(prefix="/ai", tags=["ai"])


@router.post("/generate-pitch", status_code=status.HTTP_202_ACCEPTED)
def generate_pitch(
    company_name: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_identity: User = Depends(rate_limited_identity),
):
    campaign = AICampaign(company_name=company_name, status="pending")
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    # Pass only the campaign_id and company_name — NOT this request's db
    # session, since it will already be closed by the time this runs.
    background_tasks.add_task(execute_ai_sdr_workflow, campaign.id, company_name)

    return {"campaign_id": campaign.id, "status": "pending"}