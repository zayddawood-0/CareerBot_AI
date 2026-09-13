# Backend implementation notes

This folder implements the `backend/` portion of the CareerBot AI structure
described in the project README, ready to drop into your fork at
`careerbot-ai/backend/`.

## What's implemented

- `main.py` — FastAPI app, CORS, router registration, dev auto-create-tables
- `config.py` — pydantic-settings config loaded from `.env`
- `database.py` — SQLAlchemy engine/session/Base
- `models/` — User, Resume, AgentState, Job (matches the README's DB schema)
- `schemas/` — Pydantic request/response models for all three routers
- `services/resume_parser.py` — PyMuPDF (PDF) + python-docx (DOCX) text extraction
- `services/ai_service.py` — Gemini 1.5 Flash resume parsing + batched job
  scoring, with automatic Groq fallback on quota/errors
- `services/job_scraper.py` — JobSpy wrapper (LinkedIn/Indeed/Glassdoor),
  24-hour filter, mock-data fallback from `tests/mock_data/sample_jobs.json`
- `services/scheduler.py` — APScheduler daily 9:00 AM cron per agent +
  synchronous "run now" trigger; this is the actual agent loop
- `routers/resume.py`, `routers/agent.py`, `routers/jobs.py` — the 7
  endpoints listed in the README's API Reference
- `routers/dependencies.py` — session-ID-based MVP auth (`X-Session-Id`
  header), auto-creates a `User` row on first sight, per the README's
  "Development Shortcuts" section
- `alembic.ini`, `alembic/env.py`, `alembic/script.py.mako` — migration
  scaffolding wired to `Base.metadata` and `config.settings`
- `Dockerfile` — matches the Docker Compose setup in the README

## One thing I made an explicit decision on

The README's `GET /api/agent/status` doesn't say how the agent is
identified. I added `agent_id` as a required query parameter
(`GET /api/agent/status?agent_id=...`), since a user could in principle run
more than one agent. Same for `/stop` and `/run-now`. If your frontend
expects a single implicit "current agent" instead, say so and I'll change it
to look up the user's most recent `AgentState` automatically.

## Not implemented (intentionally, per your ask for "the backend portion")

- Frontend (`frontend/`) — not part of this request
- Real user auth / passwords — README explicitly scopes this out for the MVP
- Email/push notifications, per-job resume tailoring, application tracking —
  these are unchecked Roadmap items, not part of the current feature set
