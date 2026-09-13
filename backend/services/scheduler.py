"""
Owns the actual "Loop Engineering" agent loop:

  scheduler.start_for_agent(agent_id)   -> registers a daily 9:00 AM job
  scheduler.stop_for_agent(agent_id)    -> cancels it, agent goes IDLE
  scheduler.run_now(agent_id)           -> runs the scan immediately (sync)

_execute_scan() is the actual pipeline: scrape -> AI score -> persist ->
update agent_state. It opens its own DB session because APScheduler jobs
run outside any FastAPI request context.
"""
import logging
from datetime import datetime, timezone

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from config import settings
from database import SessionLocal
from models.agent_state import AgentState, AgentStatus
from models.job import Job
from models.resume import Resume
from schemas.resume import ResumeParsed
from services import ai_service, job_scraper

logger = logging.getLogger(__name__)

_scheduler = BackgroundScheduler()
_scheduler.start()


def _job_id_for(agent_id: str) -> str:
    return f"agent-scan-{agent_id}"


def start_for_agent(agent_id: str) -> datetime:
    """Registers the daily cron trigger for this agent and returns next_run."""
    trigger = CronTrigger(hour=settings.agent_run_hour, minute=settings.agent_run_minute)
    _scheduler.add_job(
        _execute_scan,
        trigger=trigger,
        args=[agent_id],
        id=_job_id_for(agent_id),
        replace_existing=True,
        misfire_grace_time=3600,
    )
    job = _scheduler.get_job(_job_id_for(agent_id))
    return job.next_run_time


def stop_for_agent(agent_id: str) -> None:
    job_id = _job_id_for(agent_id)
    if _scheduler.get_job(job_id):
        _scheduler.remove_job(job_id)


def run_now(agent_id: str) -> None:
    """Synchronous immediate execution, used by POST /api/agent/run-now."""
    _execute_scan(agent_id)


def get_next_run(agent_id: str) -> datetime | None:
    job = _scheduler.get_job(_job_id_for(agent_id))
    return job.next_run_time if job else None


# ---------------------------------------------------------------------------
# Core pipeline
# ---------------------------------------------------------------------------

def _execute_scan(agent_id: str) -> None:
    db = SessionLocal()
    try:
        agent = db.get(AgentState, agent_id)
        if agent is None:
            logger.warning("Agent %s no longer exists, skipping scan", agent_id)
            return

        agent.status = AgentStatus.RUNNING
        db.commit()

        resume = db.get(Resume, agent.resume_id)
        resume_parsed = ResumeParsed(
            skills=resume.parsed_skills,
            titles=resume.parsed_titles,
            experience_years=resume.experience_years,
        )

        search_term = resume_parsed.titles[0] if resume_parsed.titles else agent.user_prompt
        raw_jobs = job_scraper.scrape_recent_jobs(search_term=search_term)
        scored_jobs = ai_service.score_jobs(resume_parsed, agent.user_prompt, raw_jobs)

        for scored in scored_jobs:
            db.add(
                Job(
                    agent_id=agent.id,
                    title=scored.title,
                    company=scored.company,
                    description_summary=scored.description_summary,
                    salary_min=scored.salary_min,
                    salary_max=scored.salary_max,
                    work_mode=scored.work_mode,
                    location=scored.location,
                    apply_url=scored.apply_url,
                    match_score=scored.match_score,
                    match_reason=scored.match_reason,
                    posted_at=scored.posted_at,
                    source=scored.source,
                )
            )

        agent.status = AgentStatus.ACTIVE
        agent.last_run_at = datetime.now(timezone.utc)
        agent.next_run_at = get_next_run(agent_id)
        agent.total_runs += 1
        agent.last_error = None
        db.commit()

    except Exception as exc:  # noqa: BLE001 - a failed scan should never crash the scheduler thread
        logger.exception("Agent scan failed for %s", agent_id)
        db.rollback()
        agent = db.get(AgentState, agent_id)
        if agent:
            agent.status = AgentStatus.ERROR
            agent.last_error = str(exc)
            db.commit()
    finally:
        db.close()
