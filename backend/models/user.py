import uuid
from datetime import datetime, timezone

from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class User(Base):
    """
    Hackathon MVP auth: a user row is created the first time a browser
    session ID is seen (see routers/dependencies), no password involved.
    """
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    session_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    resumes: Mapped[list["Resume"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    agent_states: Mapped[list["AgentState"]] = relationship(back_populates="user", cascade="all, delete-orphan")
