import os
import uuid

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models.resume import Resume
from models.user import User
from routers.dependencies import get_current_user
from schemas.resume import ResumeUploadResponse
from services import resume_parser, ai_service
from services.resume_parser import UnsupportedResumeFormat

router = APIRouter(prefix="/api/resume", tags=["resume"])

ALLOWED_EXTENSIONS = {".pdf", ".docx"}


@router.post("/upload", response_model=ResumeUploadResponse)
def upload_resume(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Only .pdf and .docx resumes are accepted.")

    os.makedirs(settings.upload_dir, exist_ok=True)
    stored_name = f"{uuid.uuid4()}{ext}"
    stored_path = os.path.join(settings.upload_dir, stored_name)

    with open(stored_path, "wb") as out_file:
        out_file.write(file.file.read())

    try:
        raw_text = resume_parser.extract_text(stored_path)
    except UnsupportedResumeFormat as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if not raw_text.strip():
        raise HTTPException(status_code=422, detail="Could not extract any text from this resume file.")

    try:
        parsed = ai_service.parse_resume(raw_text)
    except ai_service.AIServiceError as exc:
        raise HTTPException(status_code=502, detail=f"AI resume parsing failed: {exc}") from exc

    resume = Resume(
        user_id=current_user.id,
        file_path=stored_path,
        raw_text=raw_text,
        parsed_skills=parsed.skills,
        parsed_titles=parsed.titles,
        experience_years=parsed.experience_years,
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    return ResumeUploadResponse(resume_id=resume.id, parsed=parsed)
