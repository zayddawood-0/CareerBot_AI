import enum
import uuid
from datetime import datetime

from sqlalchemy import String, Integer, DateTime, ForeignKey, Enum, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class AgentStatus(str, enum.Enum):
    IDLE = "IDLE"
    ACTIVE = "ACTIVE"
    RUNNING = "RUNNING"   # currently mid-scan
    ERROR = "ERROR"


class AgentState(Base):
    __tablename__ = "agent_state"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String, ForeignKey("users.id"))
    resume_id: Mapped[str] = mapped_column(String, ForeignKey("resumes.id"))

    user_prompt: Mapped[str] = mapped_column(Text)
    status: Mapped[AgentStatus] = mapped_column(Enum(AgentStatus), default=AgentStatus.IDLE)

    next_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    total_runs: Mapped[int] = mapped_column(Integer, default=0)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(back_populates="agent_states")
    jobs: Mapped[list["Job"]] = relationship(back_populates="agent", cascade="all, delete-orphan")
