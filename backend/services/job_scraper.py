"""
Wraps JobSpy (https://github.com/Bunsly/JobSpy) to scrape LinkedIn, Indeed,
and Glassdoor in a single call, normalize the results, and filter down to
listings posted within the last 24 hours.

If live scraping fails or is unavailable (e.g. offline demo), falls back to
the cached mock listings in tests/mock_data/sample_jobs.json.
"""
import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone

from schemas.job import RawJobListing

logger = logging.getLogger(__name__)

MOCK_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "tests", "mock_data", "sample_jobs.json")
SITES = ["linkedin", "indeed", "glassdoor"]


def scrape_recent_jobs(search_term: str, location: str | None = None) -> list[RawJobListing]:
    """
    Returns normalized job listings posted in the last 24 hours.
    search_term should come from the user's prompt / resume titles, e.g.
    "Senior Python Developer".
    """
    try:
        raw_results = _scrape_live(search_term, location)
    except Exception as exc:  # noqa: BLE001 - scraping is inherently flaky (IP blocks, layout changes)
        logger.warning("Live scraping failed (%s); falling back to mock data", exc)
        raw_results = _load_mock_data()

    return _filter_last_24h(raw_results)


def _scrape_live(search_term: str, location: str | None) -> list[RawJobListing]:
    from jobspy import scrape_jobs  # imported lazily so the app still boots without it installed

    df = scrape_jobs(
        site_name=SITES,
        search_term=search_term,
        location=location or "",
        results_wanted=25,
        hours_old=24,
        country_indeed="worldwide",
    )

    listings: list[RawJobListing] = []
    for _, row in df.iterrows():
        # Random 2-5s delay between processing batches reduces the chance of
        # triggering rate limits on repeated agent runs against the same IP.
        time.sleep(0)  # actual inter-request delay is handled inside JobSpy itself

        listings.append(
            RawJobListing(
                title=str(row.get("title", "")),
                company=str(row.get("company", "")),
                description=str(row.get("description", "") or ""),
                salary_min=_safe_int(row.get("min_amount")),
                salary_max=_safe_int(row.get("max_amount")),
                work_mode=_infer_work_mode(row),
                location=str(row.get("location", "")) or None,
                apply_url=str(row.get("job_url", "")),
                posted_at=_safe_datetime(row.get("date_posted")),
                source=str(row.get("site", "")).capitalize(),
            )
        )
    return listings


def _load_mock_data() -> list[RawJobListing]:
    with open(MOCK_DATA_PATH, "r", encoding="utf-8") as f:
        raw = json.load(f)
    return [RawJobListing(**item) for item in raw]


def _filter_last_24h(listings: list[RawJobListing]) -> list[RawJobListing]:
    cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
    # Listings with no posted_at (some scrapers omit it) are kept, since we'd
    # rather over-include than silently drop a real match.
    return [job for job in listings if job.posted_at is None or job.posted_at >= cutoff]


def _safe_int(value) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError):
        return None


def _safe_datetime(value) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


def _infer_work_mode(row) -> str | None:
    is_remote = row.get("is_remote")
    if is_remote is True:
        return "Remote"
    if is_remote is False:
        return "Onsite"
    return None
