"""
Ashby job board scraper.

Uses the public Ashby Posting API which requires no authentication.
API: GET https://api.ashbyhq.com/posting-api/job-board/{board_id}
"""

from config.companies import CompanyConfig, get_companies_by_platform
from scrapers.base_scraper import BaseScraper, JobListing
from utils.logger import get_logger

logger = get_logger("scraper.ashby")

_API_BASE = "https://api.ashbyhq.com/posting-api/job-board"


class AshbyScraper(BaseScraper):
    """Scrapes jobs from Ashby-powered career pages via their public API."""

    @property
    def source_name(self) -> str:
        return "ashby"

    def __init__(self, companies: list[CompanyConfig] | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._companies = companies or get_companies_by_platform("ashby")

    def _scrape_company(self, company: CompanyConfig) -> list[JobListing]:
        """Scrape all jobs from a single Ashby board."""
        url = f"{_API_BASE}/{company.board_id}"

        try:
            data = self._get_json(url)
        except Exception as e:
            logger.warning(f"Failed to scrape {company.name}: {e}")
            return []

        jobs = []
        # Ashby returns jobs nested under departments/teams
        job_postings = data.get("jobs", [])

        for posting in job_postings:
            try:
                # Extract location
                location = posting.get("location", "")
                if isinstance(location, dict):
                    location = location.get("name", "")

                # Build description
                description = posting.get("descriptionPlain", "")
                if not description and posting.get("descriptionHtml"):
                    from bs4 import BeautifulSoup
                    description = BeautifulSoup(
                        posting["descriptionHtml"], "lxml"
                    ).get_text(separator="\n", strip=True)

                # Build URL
                job_url = posting.get("jobUrl", "")
                if not job_url and posting.get("id"):
                    job_url = f"https://jobs.ashbyhq.com/{company.board_id}/{posting['id']}"

                listing = JobListing(
                    company=company.name,
                    title=posting.get("title", ""),
                    url=job_url,
                    location=location if isinstance(location, str) else "",
                    description=description,
                    source=self.source_name,
                    posted_date=posting.get("publishedAt", ""),
                )
                jobs.append(listing)
            except Exception as e:
                logger.debug(f"Error parsing Ashby posting from {company.name}: {e}")
                continue

        logger.info(f"[Ashby] {company.name}: found {len(jobs)} jobs")
        return jobs

    def scrape(self) -> list[JobListing]:
        """Scrape all configured Ashby boards."""
        all_jobs: list[JobListing] = []

        for company in self._companies:
            jobs = self._scrape_company(company)
            all_jobs.extend(jobs)
            self._polite_delay(0.5, 1.5)

        logger.info(f"[Ashby] Total: {len(all_jobs)} jobs from {len(self._companies)} boards")
        return all_jobs
