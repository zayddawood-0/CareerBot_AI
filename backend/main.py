import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from database import Base, engine
import models  # noqa: F401 - ensures every model is registered on Base.metadata
from routers import resume, agent, jobs

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title="CareerBot AI",
    description="Autonomous AI-powered job finding assistant — backend API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(resume.router)
app.include_router(agent.router)
app.include_router(jobs.router)


@app.on_event("startup")
def on_startup():
    # For local/dev convenience only — production should rely on Alembic
    # migrations (`alembic upgrade head`) instead of create_all().
    if settings.database_url.startswith("sqlite"):
        Base.metadata.create_all(bind=engine)


@app.get("/health", tags=["meta"])
def health_check():
    return {"status": "ok"}
