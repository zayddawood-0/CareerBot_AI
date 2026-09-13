from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, asc
from sqlalchemy.orm import Session

from database import get_db
from models.agent_state import AgentState
from models.job import Job
from models.user import User
from routers.dependencies import get_current_user
from schemas.job import JobOut, PaginatedJobs

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

SORTABLE_FIELDS = {
    "match_score": Job.match_score,
    "posted_at": Job.posted_at,
    "found_at": Job.found_at,
    "salary_max": Job.salary_max,
}


@router.get("", response_model=PaginatedJobs)
def list_jobs(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: Literal["match_score", "posted_at", "found_at", "salary_max"] = "match_score",
    sort_dir: Literal["asc", "desc"] = "desc",
    work_mode: str | None = None,
    min_score: int | None = Query(None, ge=0, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Jobs belong to agents, agents belong to the current user — this join
    # keeps the endpoint scoped to only what this user's agent(s) have found.
    query = db.query(Job).join(AgentState).filter(AgentState.user_id == current_user.id)

    if work_mode:
        query = query.filter(Job.work_mode == work_mode)
    if min_score is not None:
        query = query.filter(Job.match_score >= min_score)

    sort_column = SORTABLE_FIELDS[sort_by]
    query = query.order_by(desc(sort_column) if sort_dir == "desc" else asc(sort_column))

    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return PaginatedJobs(total=total, page=page, page_size=page_size, items=items)


@router.get("/{job_id}", response_model=JobOut)
def get_job(
    job_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    job = (
        db.query(Job)
        .join(AgentState)
        .filter(Job.id == job_id, AgentState.user_id == current_user.id)
        .first()
    )
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found for this user.")
    return job
