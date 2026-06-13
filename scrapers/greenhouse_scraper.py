"""
Greenhouse job board scraper.

Uses the public Greenhouse Job Board API which requires no authentication.
API docs: https://developers.greenhouse.io/job-board.html

Endpoint: GET https://api.greenhouse.io/v1/boards/{board_token}/jobs?content=true
"""

from bs4 import BeautifulSoup

from config.companies import CompanyConfig, get_companies_by_platform
from scrapers.base_scraper import BaseScraper, JobListing
from utils.logger import get_logger

logger = get_logger("scraper.greenhouse")

_API_BASE = "https://api.greenhouse.io/v1/boards"


class GreenhouseScraper(BaseScraper):
    """Scrapes jobs from Greenhouse-powered career pages via their public API."""

    @property
    def source_name(self) -> str:
        return "greenhouse"

    def __init__(self, companies: list[CompanyConfig] | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._companies = companies or get_companies_by_platform("greenhouse")

    def _clean_html(self, html_content: str) -> str:
        """Strip HTML tags from job description content."""
        if not html_content:
            return ""
        soup = BeautifulSoup(html_content, "lxml")
        return soup.get_text(separator="\n", strip=True)

    def _scrape_company(self, company: CompanyConfig, limit: int | None = None) -> list[JobListing]:
        """Scrape all jobs from a single Greenhouse board."""
        url = f"{_API_BASE}/{company.board_id}/jobs"
        params = {"content": "true"}

        try:
            data = self._get_json(url, params=params)
        except Exception as e:
            logger.warning(f"Failed to scrape {company.name}: {e}")
            return []

        jobs = []
        for job_data in data.get("jobs", []):
            if limit is not None and len(jobs) >= limit:
                break
            try:
                # Extract location
                location = ""
                if job_data.get("location", {}).get("name"):
                    location = job_data["location"]["name"]

                # Extract and clean description
                description = self._clean_html(
                    job_data.get("content", "")
                )

                listing = JobListing(
                    company=company.name,
                    title=job_data.get("title", ""),
                    url=job_data.get("absolute_url", ""),
                    location=location,
                    description=description,
                    source=self.source_name,
                    posted_date=job_data.get("updated_at", ""),
                )
                jobs.append(listing)
            except Exception as e:
                logger.debug(f"Error parsing job from {company.name}: {e}")
                continue

        logger.info(f"[Greenhouse] {company.name}: found {len(jobs)} jobs")
        return jobs

    def scrape(self) -> list[JobListing]:
        """Scrape all configured Greenhouse boards."""
        all_jobs: list[JobListing] = []

        for company in self._companies:
            if self._max_jobs_limit is not None and len(all_jobs) >= self._max_jobs_limit:
                break
            rem_limit = None
            if self._max_jobs_limit is not None:
                rem_limit = self._max_jobs_limit - len(all_jobs)

            # Respect company-specific limit if set
            comp_limit = company.scraping_limit if getattr(company, 'scraping_limit', None) is not None else None
            if comp_limit is not None:
                limit_to_use = min(comp_limit, rem_limit) if rem_limit is not None else comp_limit
            else:
                limit_to_use = rem_limit

            jobs = self._scrape_company(company, limit=limit_to_use)
            all_jobs.extend(jobs)
            self._polite_delay(0.5, 1.5)  # Be polite between companies

        logger.info(f"[Greenhouse] Total: {len(all_jobs)} jobs from {len(self._companies)} boards")
        return all_jobs
