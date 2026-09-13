"""
All AI calls live here: resume field extraction and batched job scoring.
Gemini 1.5 Flash is primary; Groq (Llama 3) is the automatic fallback if
Gemini's free-tier quota (1500/day, 15/min) is exhausted or errors out.
"""
import json
import logging

import google.generativeai as genai
from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential

from config import settings
from schemas.job import RawJobListing, ScoredJobListing
from schemas.resume import ResumeParsed

logger = logging.getLogger(__name__)

if settings.gemini_api_key:
    genai.configure(api_key=settings.gemini_api_key)

_gemini_model = None
_groq_client = Groq(api_key=settings.groq_api_key) if settings.groq_api_key else None

# Batch size for job scoring — keeps us well within Gemini's 15 req/min limit
# even on a large scrape, since one call scores many jobs at once.
JOB_SCORE_BATCH_SIZE = 10


def _get_gemini_model():
    global _gemini_model
    if _gemini_model is None:
        _gemini_model = genai.GenerativeModel("gemini-1.5-flash")
    return _gemini_model


class AIServiceError(Exception):
    pass


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def _call_gemini(prompt: str) -> str:
    model = _get_gemini_model()
    response = model.generate_content(
        prompt,
        generation_config={"response_mime_type": "application/json"},
    )
    return response.text


def _call_groq(prompt: str) -> str:
    if _groq_client is None:
        raise AIServiceError("No Groq API key configured — cannot fall back.")
    completion = _groq_client.chat.completions.create(
        model="openai/gpt-oss-120b",
        messages=[
            {"role": "system", "content": "You always respond with valid JSON only, no prose, no markdown fences."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
    )
    return completion.choices[0].message.content


def _call_ai(prompt: str) -> dict:
    """Try Gemini first, fall back to Groq, then raise if both fail."""
    raw = None
    try:
        raw = _call_gemini(prompt)
    except Exception as exc:  # noqa: BLE001 - Gemini can fail for many reasons (quota, network, etc.)
        logger.warning("Gemini call failed (%s), falling back to Groq", exc)
        try:
            raw = _call_groq(prompt)
        except Exception as fallback_exc:  # noqa: BLE001
            raise AIServiceError(f"Both Gemini and Groq failed: {fallback_exc}") from fallback_exc

    cleaned = raw.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise AIServiceError(f"AI provider returned non-JSON output: {raw[:200]}") from exc


# ---------------------------------------------------------------------------
# Resume parsing
# ---------------------------------------------------------------------------

def parse_resume(raw_text: str) -> ResumeParsed:
    """Extract skills, past job titles, and years of experience from resume text."""
    prompt = f"""
You are a resume parser. Read the resume text below and return ONLY a JSON
object with this exact shape, nothing else:

{{
  "skills": ["skill1", "skill2", ...],
  "titles": ["past job title 1", "past job title 2", ...],
  "experience_years": <integer, your best estimate of total years of professional experience>
}}

Resume text:
---
{raw_text[:8000]}
---
""".strip()

    data = _call_ai(prompt)
    return ResumeParsed(
        skills=data.get("skills", []),
        titles=data.get("titles", []),
        experience_years=data.get("experience_years"),
    )


# ---------------------------------------------------------------------------
# Job scoring
# ---------------------------------------------------------------------------

def score_jobs(
    resume: ResumeParsed,
    user_prompt: str,
    jobs: list[RawJobListing],
) -> list[ScoredJobListing]:
    """
    Score a list of raw scraped jobs against the resume + user's stated intent.
    Batches jobs to stay within Gemini's free-tier rate limits.
    """
    scored: list[ScoredJobListing] = []

    for start in range(0, len(jobs), JOB_SCORE_BATCH_SIZE):
        batch = jobs[start:start + JOB_SCORE_BATCH_SIZE]
        scored.extend(_score_batch(resume, user_prompt, batch))

    return scored


def _score_batch(
    resume: ResumeParsed,
    user_prompt: str,
    batch: list[RawJobListing],
) -> list[ScoredJobListing]:
    listings_payload = [
        {
            "index": i,
            "title": job.title,
            "company": job.company,
            "description": job.description[:1500],
        }
        for i, job in enumerate(batch)
    ]

    prompt = f"""
You are a job-matching engine. The candidate's parsed resume and stated
preference are below, followed by a list of job listings. For EACH listing,
return a match_score (0-100) and a one-sentence match_reason explaining the
score in plain English, plus a 1-2 sentence description_summary of the role.

Return ONLY a JSON object of this exact shape:
{{
  "results": [
    {{"index": 0, "match_score": 92, "match_reason": "...", "description_summary": "..."}},
    ...
  ]
}}

Candidate skills: {resume.skills}
Candidate past titles: {resume.titles}
Candidate experience (years): {resume.experience_years}
Candidate's stated preference: "{user_prompt}"

Job listings:
{json.dumps(listings_payload, indent=2)}
""".strip()

    data = _call_ai(prompt)
    results_by_index = {r["index"]: r for r in data.get("results", [])}

    scored_batch: list[ScoredJobListing] = []
    for i, job in enumerate(batch):
        result = results_by_index.get(i, {})
        scored_batch.append(
            ScoredJobListing(
                **job.model_dump(),
                description_summary=result.get("description_summary", job.description[:200]),
                match_score=int(result.get("match_score", 0)),
                match_reason=result.get("match_reason", "No match reason returned by AI provider."),
            )
        )
    return scored_batch
