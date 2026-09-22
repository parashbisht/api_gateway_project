from sqlalchemy import Column, Integer, String, Text, DateTime
from datetime import datetime
from app.db.base import Base  # Hooks into your existing base DB setup

class AICampaign(Base):
    __tablename__ = "ai_campaigns"
    
    id = Column(Integer, primary_key=True, index=True)
    company_name = Column(String, nullable=False, index=True)
    research_summary = Column(Text, nullable=True)
    generated_pitch = Column(Text, nullable=True)
    status = Column(String, default="pending")  # pending, processing, completed, failed
    created_at = Column(DateTime, default=datetime.utcnow)
