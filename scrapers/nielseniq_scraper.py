"""
NielsenIQ Job Scraper.

Uses CareerSourceDetector to verify ATS platform (SmartRecruiters) and queries SmartRecruiters API.
"""

from scrapers.base_scraper import BaseScraper, JobListing
from utils.career_source_detector import CareerSourceDetector
from utils.logger import get_logger

logger = get_logger("scraper.nielseniq")


class NielseniqScraper(BaseScraper):
    """Scrapes jobs from NielsenIQ's SmartRecruiters portal."""

    @property
    def source_name(self) -> str:
        return "nielseniq"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.company_name = "NielsenIQ"
        self.fallback_url = "https://careers.smartrecruiters.com/NielsenIQ"
        self.detector = CareerSourceDetector()

    def scrape(self) -> list[JobListing]:
        """Scrape jobs from NielsenIQ SmartRecruiters API."""
        jobs: list[JobListing] = []
        try:
            info = self.detector.detect(self.company_name, self.fallback_url)
            platform = info.get("platform", "SmartRecruiters")
            api_endpoint = info.get("api_endpoint", "https://api.smartrecruiters.com/v1/companies/NielsenIQ/postings")

            logger.info(f"[{self.company_name}] Detected platform: {platform}")

            if platform == "SmartRecruiters":
                data = self._get_json(api_endpoint)
                postings = data.get("content", [])
                logger.info(f"[{self.company_name}] SmartRecruiters API returned {len(postings)} postings")

                for item in postings:
                    if self._max_jobs_limit and len(jobs) >= self._max_jobs_limit:
                        break

                    title = item.get("title", "")
                    uuid = item.get("uuid", "")
                    job_url = f"https://jobs.smartrecruiters.com/NielsenIQ/{uuid}"
                    
                    loc_data = item.get("location", {})
                    city = loc_data.get("city", "")
                    country = loc_data.get("country", "")
                    location = f"{city}, {country}" if city and country else (city or country or "India")
                    
                    posted_date = item.get("releasedDate", "")
                    
                    listing = JobListing(
                        company=self.company_name,
                        title=title,
                        url=job_url,
                        location=location,
                        description=f"NielsenIQ SmartRecruiters job listing: {title}. Location: {location}.",
                        source=self.source_name,
                        posted_date=posted_date,
                        company_priority=95
                    )
                    jobs.append(listing)
            else:
                logger.warning(f"[{self.company_name}] Discovered non-SmartRecruiters platform. Skipping API scrape.")
        except Exception as e:
            logger.error(f"[{self.company_name}] Scraper failed: {e}", exc_info=True)

        print(f"[NielsenIQ]\nQuery: postings\nJobs Found: {len(jobs)}\nJobs Parsed: {len(jobs)}")
        return jobs
