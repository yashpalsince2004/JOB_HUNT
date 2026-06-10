"""
SmartRecruiters job board scraper.

Uses the public SmartRecruiters API.
API: GET https://api.smartrecruiters.com/v1/companies/{company_id}/postings
"""

from config.companies import CompanyConfig, get_companies_by_platform
from scrapers.base_scraper import BaseScraper, JobListing
from utils.logger import get_logger

logger = get_logger("scraper.smartrecruiters")

_API_BASE = "https://api.smartrecruiters.com/v1/companies"


class SmartRecruitersScraper(BaseScraper):
    """Scrapes jobs from SmartRecruiters-powered career pages."""

    @property
    def source_name(self) -> str:
        return "smartrecruiters"

    def __init__(self, companies: list[CompanyConfig] | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._companies = companies or get_companies_by_platform("smartrecruiters")

    def _scrape_company(self, company: CompanyConfig) -> list[JobListing]:
        """Scrape all jobs from a single SmartRecruiters company."""
        all_jobs: list[JobListing] = []
        offset = 0
        limit = 100  # Max per page

        while True:
            url = f"{_API_BASE}/{company.board_id}/postings"
            params = {"offset": offset, "limit": limit}

            try:
                data = self._get_json(url, params=params)
            except Exception as e:
                logger.warning(f"Failed to scrape {company.name} (offset={offset}): {e}")
                break

            postings = data.get("content", [])
            if not postings:
                break

            for posting in postings:
                try:
                    # Extract location
                    location_data = posting.get("location", {})
                    location_parts = []
                    if location_data.get("city"):
                        location_parts.append(location_data["city"])
                    if location_data.get("region"):
                        location_parts.append(location_data["region"])
                    if location_data.get("country"):
                        location_parts.append(location_data["country"])
                    location = ", ".join(location_parts)

                    # Build description from sections
                    description = ""
                    company_desc = posting.get("company", {}).get("description", "")
                    job_desc = posting.get("name", "")

                    # Get full job details via individual posting endpoint
                    # (the list endpoint has limited info)
                    posting_id = posting.get("id", "")
                    if posting_id:
                        try:
                            detail_url = f"{_API_BASE}/{company.board_id}/postings/{posting_id}"
                            detail = self._get_json(detail_url)
                            sections = detail.get("jobAd", {}).get("sections", {})
                            desc_parts = []
                            for section_name in ["jobDescription", "qualifications", "additionalInformation"]:
                                section = sections.get(section_name, {})
                                if section.get("text"):
                                    from bs4 import BeautifulSoup
                                    desc_parts.append(
                                        BeautifulSoup(section["text"], "lxml").get_text(separator="\n", strip=True)
                                    )
                            description = "\n\n".join(desc_parts)
                            self._polite_delay(0.3, 0.8)
                        except Exception:
                            description = company_desc

                    listing = JobListing(
                        company=company.name,
                        title=posting.get("name", ""),
                        url=f"https://jobs.smartrecruiters.com/{company.board_id}/{posting_id}",
                        location=location,
                        description=description,
                        source=self.source_name,
                        posted_date=posting.get("releasedDate", ""),
                    )
                    all_jobs.append(listing)
                except Exception as e:
                    logger.debug(f"Error parsing SmartRecruiters posting: {e}")
                    continue

            # Pagination
            total_found = data.get("totalFound", 0)
            offset += limit
            if offset >= total_found:
                break
            self._polite_delay(0.5, 1.0)

        logger.info(f"[SmartRecruiters] {company.name}: found {len(all_jobs)} jobs")
        return all_jobs

    def scrape(self) -> list[JobListing]:
        """Scrape all configured SmartRecruiters companies."""
        all_jobs: list[JobListing] = []

        for company in self._companies:
            jobs = self._scrape_company(company)
            all_jobs.extend(jobs)
            self._polite_delay(1.0, 2.0)

        logger.info(
            f"[SmartRecruiters] Total: {len(all_jobs)} jobs "
            f"from {len(self._companies)} companies"
        )
        return all_jobs
