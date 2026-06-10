"""
Lever job board scraper.

Uses the public Lever Postings API which requires no authentication.
API: GET https://api.lever.co/v0/postings/{company}?mode=json
"""

from config.companies import CompanyConfig, get_companies_by_platform
from scrapers.base_scraper import BaseScraper, JobListing
from utils.logger import get_logger

logger = get_logger("scraper.lever")

_API_BASE = "https://api.lever.co/v0/postings"


class LeverScraper(BaseScraper):
    """Scrapes jobs from Lever-powered career pages via their public API."""

    @property
    def source_name(self) -> str:
        return "lever"

    def __init__(self, companies: list[CompanyConfig] | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._companies = companies or get_companies_by_platform("lever")

    def _scrape_company(self, company: CompanyConfig) -> list[JobListing]:
        """Scrape all jobs from a single Lever company board."""
        url = f"{_API_BASE}/{company.board_id}"
        params = {"mode": "json"}

        try:
            data = self._get_json(url, params=params)
        except Exception as e:
            logger.warning(f"Failed to scrape {company.name}: {e}")
            return []

        # Lever returns a flat list of job postings
        if not isinstance(data, list):
            logger.warning(f"Unexpected response format from {company.name}")
            return []

        jobs = []
        for posting in data:
            try:
                # Build description from categories and lists
                desc_parts = []
                if posting.get("descriptionPlain"):
                    desc_parts.append(posting["descriptionPlain"])

                # Lever has structured "lists" for requirements, etc.
                for lst in posting.get("lists", []):
                    if lst.get("text"):
                        desc_parts.append(lst["text"])
                    if lst.get("content"):
                        # Content is HTML, but we'll take plain text
                        from bs4 import BeautifulSoup
                        desc_parts.append(
                            BeautifulSoup(lst["content"], "lxml").get_text(separator="\n", strip=True)
                        )

                # Extract location from categories
                location = ""
                categories = posting.get("categories", {})
                if categories.get("location"):
                    location = categories["location"]
                elif categories.get("allLocations"):
                    location = ", ".join(categories["allLocations"])

                listing = JobListing(
                    company=company.name,
                    title=posting.get("text", ""),
                    url=posting.get("hostedUrl", posting.get("applyUrl", "")),
                    location=location,
                    description="\n".join(desc_parts),
                    source=self.source_name,
                    posted_date=str(posting.get("createdAt", "")),
                )
                jobs.append(listing)
            except Exception as e:
                logger.debug(f"Error parsing Lever posting from {company.name}: {e}")
                continue

        logger.info(f"[Lever] {company.name}: found {len(jobs)} jobs")
        return jobs

    def scrape(self) -> list[JobListing]:
        """Scrape all configured Lever boards."""
        all_jobs: list[JobListing] = []

        for company in self._companies:
            jobs = self._scrape_company(company)
            all_jobs.extend(jobs)
            self._polite_delay(0.5, 1.5)

        logger.info(f"[Lever] Total: {len(all_jobs)} jobs from {len(self._companies)} boards")
        return all_jobs
