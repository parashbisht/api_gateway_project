from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, func
from app.db.base import Base


class RequestLog(Base):
    __tablename__ = "request_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)  # null if unauthenticated
    endpoint = Column(String, nullable=False)
    method = Column(String, nullable=False)
    ip_address = Column(String, nullable=False)
    status_code = Column(Integer, nullable=False)
    response_time_ms = Column(Float, nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())