"""
Import every model here so `Base.metadata` sees all tables — this is what
Alembic's autogenerate relies on to detect the full schema.
"""
from models.user import User
from models.resume import Resume
from models.agent_state import AgentState
from models.job import Job

__all__ = ["User", "Resume", "AgentState", "Job"]
