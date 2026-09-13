import uuid
from datetime import datetime

from sqlalchemy import String, Integer, Text, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id: Mapped[str] = mapped_column(String, ForeignKey("agent_state.id"))

    title: Mapped[str] = mapped_column(String)
    company: Mapped[str] = mapped_column(String)
    description_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    salary_min: Mapped[int | None] = mapped_column(Integer, nullable=True)
    salary_max: Mapped[int | None] = mapped_column(Integer, nullable=True)
    work_mode: Mapped[str | None] = mapped_column(String, nullable=True)   # Remote / Onsite / Hybrid
    location: Mapped[str | None] = mapped_column(String, nullable=True)

    apply_url: Mapped[str] = mapped_column(String)
    match_score: Mapped[int] = mapped_column(Integer, default=0)
    match_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    posted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    found_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    source: Mapped[str] = mapped_column(String)   # LinkedIn / Indeed / Glassdoor

    agent: Mapped["AgentState"] = relationship(back_populates="jobs")
