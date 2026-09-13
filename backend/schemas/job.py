from datetime import datetime

from pydantic import BaseModel, ConfigDict


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    company: str
    description_summary: str | None
    salary_min: int | None
    salary_max: int | None
    work_mode: str | None
    location: str | None
    apply_url: str
    match_score: int
    match_reason: str | None
    posted_at: datetime | None
    found_at: datetime
    source: str


class PaginatedJobs(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[JobOut]


class RawJobListing(BaseModel):
    """Normalized shape produced by services/job_scraper.py before AI scoring."""
    title: str
    company: str
    description: str
    salary_min: int | None = None
    salary_max: int | None = None
    work_mode: str | None = None
    location: str | None = None
    apply_url: str
    posted_at: datetime | None = None
    source: str


class ScoredJobListing(RawJobListing):
    """RawJobListing + what services/ai_service.py adds after scoring."""
    description_summary: str
    match_score: int
    match_reason: str
