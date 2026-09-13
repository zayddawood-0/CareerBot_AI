from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from database import get_db
from models.agent_state import AgentState, AgentStatus
from models.resume import Resume
from models.user import User
from routers.dependencies import get_current_user
from schemas.agent import (
    AgentStartRequest,
    AgentStartResponse,
    AgentStatusResponse,
    AgentStopResponse,
)
from services import scheduler

router = APIRouter(prefix="/api/agent", tags=["agent"])


@router.post("/start", response_model=AgentStartResponse)
def start_agent(
    payload: AgentStartRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    resume = db.get(Resume, payload.resume_id)
    if resume is None or resume.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Resume not found for this user.")

    agent = AgentState(
        user_id=current_user.id,
        resume_id=resume.id,
        user_prompt=payload.user_prompt,
        status=AgentStatus.ACTIVE,
    )
    db.add(agent)
    db.commit()
    db.refresh(agent)

    next_run = scheduler.start_for_agent(agent.id)
    agent.next_run_at = next_run
    db.commit()

    return AgentStartResponse(
        agent_id=agent.id,
        status=agent.status,
        next_run=next_run,
        message="Agent started. First scan scheduled for the next 9:00 AM run.",
    )


@router.post("/stop", response_model=AgentStopResponse)
def stop_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    agent = _get_owned_agent(db, agent_id, current_user)
    scheduler.stop_for_agent(agent.id)
    agent.status = AgentStatus.IDLE
    agent.next_run_at = None
    db.commit()

    return AgentStopResponse(agent_id=agent.id, status=agent.status, message="Agent stopped.")


@router.post("/run-now", response_model=AgentStatusResponse)
def run_now(
    agent_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    agent = _get_owned_agent(db, agent_id, current_user)
    # Runs in a background task so the request returns immediately; poll
    # GET /api/agent/status for completion, matching the "Run Now" demo flow.
    background_tasks.add_task(scheduler.run_now, agent.id)
    return AgentStatusResponse.model_validate(agent)


@router.get("/status", response_model=AgentStatusResponse)
def agent_status(
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    agent = _get_owned_agent(db, agent_id, current_user)
    return AgentStatusResponse.model_validate(agent)


def _get_owned_agent(db: Session, agent_id: str, current_user: User) -> AgentState:
    agent = db.get(AgentState, agent_id)
    if agent is None or agent.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Agent not found for this user.")
    return agent
