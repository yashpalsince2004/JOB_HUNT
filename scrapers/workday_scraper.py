"""
Workday job board scraper.

Queries Workday internal search API (wday/cxs) for MNCs using HTTP POST requests.
Avoids browser automation overhead by targeting the public API endpoints directly.
"""

from config.companies import CompanyConfig, get_companies_by_platform
from scrapers.base_scraper import BaseScraper, JobListing
from utils.logger import get_logger

logger = get_logger("scraper.workday")


class WorkdayScraper(BaseScraper):
    """Scrapes jobs from Workday career sites via their internal REST API."""

    @property
    def source_name(self) -> str:
        return "workday"

    def __init__(self, companies: list[CompanyConfig] | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._companies = companies or get_companies_by_platform("workday")

    def _get_workday_subdomain(self, company_name: str) -> str:
        """Map company name to its Workday subdomain."""
        mapping = {
            "accenture": "accenture.myworkdayjobs.com",
            "deloitte": "deloitte.myworkdayjobs.com",
            "ey": "eygbl.myworkdayjobs.com",
            "pwc": "pwc.myworkdayjobs.com",
            "quantiphi": "quantiphi.wd1.myworkdayjobs.com",
            "fractal": "fractal.myworkdayjobs.com",
        }
        return mapping.get(company_name.lower(), f"{company_name.lower()}.myworkdayjobs.com")

    def _scrape_company(self, company: CompanyConfig, limit: int | None = None) -> list[JobListing]:
        """Scrape jobs from a single Workday tenant."""
        subdomain = self._get_workday_subdomain(company.name)
        tenant = company.board_id if company.board_id else company.name.lower()
        # Standard Workday search endpoint
        url = f"https://{subdomain}/wday/cxs/{tenant}/Careers/jobs"
        
        # Fallback patterns for tenant paths
        tenant_paths = [
            f"https://{subdomain}/wday/cxs/{tenant}/Careers/jobs",
            f"https://{subdomain}/wday/cxs/{tenant}/External/jobs",
            f"https://{subdomain}/wday/cxs/{tenant}/External_Career/jobs",
        ]

        # Use search keywords configured for the company
        keywords = company.search_keywords or ("AI", "Machine Learning")
        jobs: list[JobListing] = []

        client = self._get_client()

        for search_text in keywords:
            if limit is not None and len(jobs) >= limit:
                break
            logger.info(f"[Workday] Searching {company.name} for: {search_text}")
            payload = {
                "appliedFacets": {},
                "limit": 20,
                "offset": 0,
                "searchText": search_text,
            }

            success = False
            for test_url in tenant_paths:
                try:
                    response = client.post(
                        test_url,
                        json=payload,
                        headers={
                            "Accept": "application/json",
                            "Content-Type": "application/json",
                            "Origin": f"https://{subdomain}",
                            "Referer": f"https://{subdomain}/",
                        }
                    )
                    if response.status_code == 200:
                        data = response.json()
                        success = True
                        
                        for job_data in data.get("jobPostings", []):
                            if limit is not None and len(jobs) >= limit:
                                break
                            try:
                                title = job_data.get("title", "")
                                path = job_data.get("externalPath", "")
                                job_url = f"https://{subdomain}{path}"
                                location = job_data.get("location", "")
                                posted_date = job_data.get("postedOn", "")

                                listing = JobListing(
                                    company=company.name,
                                    title=title,
                                    url=job_url,
                                    location=location,
                                    description=f"Workday Job: {title} at {company.name}. Location: {location}.",
                                    source=self.source_name,
                                    posted_date=posted_date,
                                )
                                jobs.append(listing)
                            except Exception as e:
                                logger.debug(f"Error parsing Workday job data: {e}")
                                continue
                        break # break tenant path loop if request succeeded
                except Exception as e:
                    logger.debug(f"Failed to post to {test_url}: {e}")
                    continue

            if not success:
                logger.warning(f"[Workday] Failed to fetch search results for {company.name} at all endpoints.")
            self._polite_delay(1.0, 2.5)

        logger.info(f"[Workday] {company.name}: found {len(jobs)} jobs")
        return jobs

    def scrape(self) -> list[JobListing]:
        """Scrape all configured Workday companies."""
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
            self._polite_delay(2.0, 4.0)

        logger.info(f"[Workday] Total: {len(all_jobs)} jobs from {len(self._companies)} companies")
        return all_jobs
