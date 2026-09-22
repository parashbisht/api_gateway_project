import os
from sqlalchemy.orm import Session
from crewai import Agent, Task, Crew, Process , LLM 
from crewai_tools import TavilySearchTool

from app.db.session import SessionLocal
from app.models.ai_campaign import AICampaign
from app.core.config import settings
from app.core.logger import get_logger

logger = get_logger("api_gateway.ai_worker")


def execute_ai_sdr_workflow(campaign_id: int, company_name: str) -> None:
    """
    Runs the AI SDR (sales development) workflow: research a company, then
    draft a personalized pitch. Opens its OWN database session, since this
    runs in a FastAPI BackgroundTask — the request's session is already
    closed by the time this executes.
    """
    db: Session = SessionLocal()

    try:
        campaign = db.query(AICampaign).filter(AICampaign.id == campaign_id).first()
        if not campaign:
            logger.error("AI campaign not found", extra={"campaign_id": campaign_id})
            return

        campaign.status = "processing"
        db.commit()

        llm = LLM(
            model="gemini/gemini-3.6-flash",
            api_key=settings.GEMINI_API_KEY,
            temperature=0.4,
        )
        

        search_tool = TavilySearchTool(api_key=settings.TAVILY_API_KEY)

        researcher = Agent(
            role="Lead Industry Researcher",
            goal=f"Research {company_name} and identify what they sell, their target market, and a likely pain point our AI services could solve.",
            backstory="An analyst who researches companies before outreach, so pitches are relevant instead of generic.",
            tools=[search_tool],
            llm=llm,
            verbose=True,
        )

        copywriter = Agent(
            role="B2B Conversion Copywriter",
            goal="Write a short, personalized outreach email pitching our AI services, based on the researcher's findings.",
            backstory="A copywriter specializing in concise, non-generic B2B cold email that references real details about the recipient's business.",
            llm=llm,
            verbose=True,
        )

        research_task = Task(
            description=f"Research the company '{company_name}': what they sell, their industry, and a plausible business pain point.",
            expected_output="A concise summary (3-5 sentences) of what the company does and one specific pain point.",
            agent=researcher,
        )

        pitch_task = Task(
            description="Using the research above, write a short, personalized cold email pitching our AI services to this company.",
            expected_output="A complete email: subject line + 3-4 short paragraphs, referencing a specific detail from the research.",
            agent=copywriter,
            context=[research_task],
        )

        crew = Crew(
            agents=[researcher, copywriter],
            tasks=[research_task, pitch_task],
            process=Process.sequential,
            verbose=True,
        )

        result = crew.kickoff()

        campaign.research_summary = str(research_task.output)
        campaign.generated_pitch = str(pitch_task.output)
        campaign.status = "completed"
        db.commit()

    except Exception as e:
        logger.error(
            "AI SDR workflow failed",
            extra={"campaign_id": campaign_id, "error": str(e)},
        )
        try:
            campaign = db.query(AICampaign).filter(AICampaign.id == campaign_id).first()
            if campaign:
                campaign.status = "failed"
                db.commit()
        except Exception:
            db.rollback()

    finally:
        db.close()