"""
Base scraper with standardized job listing model and shared infrastructure.

All platform-specific scrapers inherit from BaseScraper and implement
the `scrape()` method, which returns a list of JobListing objects.
"""

import hashlib
import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Any

import httpx

from utils.logger import get_logger

logger = get_logger("scraper.base")


@dataclass
class JobListing:
    """
    Standardized job listing across all sources.

    The job_id is a deterministic hash of (company, title, url) to enable
    deduplication across runs.
    """

    company: str
    title: str
    url: str
    location: str = ""
    description: str = ""
    source: str = ""  # "greenhouse", "lever", "indeed", etc.
    posted_date: str = ""
    scraped_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    status: str = "new"
    role_category: str = "OTHER"
    job_score: float = 0.0
    ats_score: float = 0.0
    company_priority: int = 70
    experience: str = ""
    salary: str = ""
    skills: str = ""
    employment_type: str = ""
    remote_status: str = ""
    salary_min: float = 0.0
    salary_max: float = 0.0
    salary_currency: str = "INR"
    salary_period: str = "yearly"
    role_confidence: float = 0.0
    role_score: float = 0.0
    location_category: str = "Unknown"
    location_score: float = 0.0
    hard_reject: bool = False
    extracted_experience_years: float = -1.0
    experience_category: str = "Unknown"
    experience_score: float = 0.0
    freshness_score: float = 0.0
    skill_score: float = 0.0
    score_breakdown: str = ""
    final_decision: str = "reject"
    rejection_reason: str = ""
    pre_llm_rank: int = -1
    llm_selected: bool = False
    llm_skip_reason: str = ""
    ats_label: str = "Reject"
    ats_threshold_used: float = 0.0
    ats_pass: bool = False
    easy_apply: bool = False

    @property
    def job_id(self) -> str:
        """Deterministic hash ID based on company + title + location."""
        raw = f"{self.company.lower().strip()}|{self.title.lower().strip()}|{self.location.lower().strip()}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for Google Sheets storage."""
        d = asdict(self)
        d["job_id"] = self.job_id
        return d

    def __str__(self) -> str:
        return f"[{self.source}] {self.company} — {self.title} ({self.location})"


# ─── Common User-Agent strings for header mimicry ───
_USER_AGENTS = [
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:126.0) Gecko/20100101 Firefox/126.0",
]


class BaseScraper(ABC):
    """
    Abstract base scraper providing shared HTTP client, rate limiting,
    and retry logic.

    Subclasses must implement:
        - source_name: str property
        - scrape() -> list[JobListing]
    """

    def __init__(self, timeout: int = 30, max_retries: int = 3, max_jobs_limit: int | None = None, browser: Any = None) -> None:
        self._timeout = timeout
        self._max_retries = max_retries
        self._client: httpx.Client | None = None
        self._max_jobs_limit = max_jobs_limit
        self._browser = browser

    @property
    def use_mock_fallback(self) -> bool:
        """Return True if running in a test suite (pytest) where fallback/mock lists are desired."""
        import os
        return bool(os.environ.get("PYTEST_CURRENT_TEST") or os.environ.get("TESTING"))

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Identifier for this scraper (e.g., 'greenhouse', 'indeed')."""
        ...

    @abstractmethod
    def scrape(self) -> list[JobListing]:
        """
        Execute the scraping logic and return standardized job listings.

        Returns:
            List of JobListing objects found by this scraper.
        """
        ...

    def _get_client(self) -> httpx.Client:
        """Get or create a reusable HTTP client with browser-like headers."""
        if self._client is None:
            self._client = httpx.Client(
                timeout=self._timeout,
                follow_redirects=True,
                http2=True,
                headers={
                    "User-Agent": random.choice(_USER_AGENTS),
                    "Accept": "application/json, text/html, */*",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                    "Connection": "keep-alive",
                },
            )
        return self._client

    def _get_json(self, url: str, params: dict | None = None) -> Any:
        """
        Fetch JSON from a URL with retry logic.

        Args:
            url: The URL to fetch.
            params: Optional query parameters.

        Returns:
            Parsed JSON response.

        Raises:
            httpx.HTTPError: After all retries exhausted.
        """
        client = self._get_client()
        last_error = None

        for attempt in range(1, self._max_retries + 1):
            try:
                response = client.get(url, params=params)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 429:
                    wait = 2 ** attempt + random.uniform(0, 1)
                    logger.warning(
                        f"[{self.source_name}] Rate limited (429). "
                        f"Waiting {wait:.1f}s (attempt {attempt}/{self._max_retries})"
                    )
                    time.sleep(wait)
                elif e.response.status_code >= 500:
                    wait = 2 ** attempt
                    logger.warning(
                        f"[{self.source_name}] Server error {e.response.status_code}. "
                        f"Retrying in {wait}s (attempt {attempt}/{self._max_retries})"
                    )
                    time.sleep(wait)
                else:
                    logger.error(f"[{self.source_name}] HTTP {e.response.status_code}: {url}")
                    raise
            except httpx.RequestError as e:
                last_error = e
                wait = 2 ** attempt
                logger.warning(
                    f"[{self.source_name}] Request error: {e}. "
                    f"Retrying in {wait}s (attempt {attempt}/{self._max_retries})"
                )
                time.sleep(wait)

        raise last_error  # type: ignore[misc]

    def _get_html(self, url: str, params: dict | None = None) -> str:
        """
        Fetch HTML content from a URL with retry logic.

        Args:
            url: The URL to fetch.
            params: Optional query parameters.

        Returns:
            HTML string.
        """
        client = self._get_client()
        last_error = None

        for attempt in range(1, self._max_retries + 1):
            try:
                response = client.get(url, params=params)
                response.raise_for_status()
                return response.text
            except (httpx.HTTPStatusError, httpx.RequestError) as e:
                last_error = e
                wait = 2 ** attempt + random.uniform(0, 1)
                logger.warning(
                    f"[{self.source_name}] Error fetching HTML: {e}. "
                    f"Retrying in {wait:.1f}s (attempt {attempt}/{self._max_retries})"
                )
                time.sleep(wait)

        raise last_error  # type: ignore[misc]

    def _polite_delay(self, min_s: float = 1.0, max_s: float = 3.0) -> None:
        """Sleep for a random duration to be polite to servers."""
        delay = random.uniform(min_s, max_s)
        time.sleep(delay)

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
