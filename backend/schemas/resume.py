from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ResumeParsed(BaseModel):
    """What ai_service.parse_resume() returns after reading the raw text."""
    skills: list[str] = []
    titles: list[str] = []
    experience_years: int | None = None


class ResumeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    file_path: str
    parsed_skills: list[str]
    parsed_titles: list[str]
    experience_years: int | None
    created_at: datetime


class ResumeUploadResponse(BaseModel):
    resume_id: str
    parsed: ResumeParsed
    message: str = "Resume parsed successfully."
