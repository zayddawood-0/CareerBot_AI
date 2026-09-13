from datetime import datetime

from pydantic import BaseModel, ConfigDict

from models.agent_state import AgentStatus


class AgentStartRequest(BaseModel):
    resume_id: str
    user_prompt: str


class AgentStartResponse(BaseModel):
    agent_id: str
    status: AgentStatus
    next_run: datetime | None
    message: str


class AgentStatusResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    status: AgentStatus
    next_run_at: datetime | None
    last_run_at: datetime | None
    total_runs: int
    last_error: str | None = None


class AgentStopResponse(BaseModel):
    agent_id: str
    status: AgentStatus
    message: str
