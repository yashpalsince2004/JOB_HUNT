"""
Fractal Analytics Job Scraper.

Uses CareerSourceDetector to identify platform (Workday) and queries the internal Workday API.
"""

from scrapers.base_scraper import BaseScraper, JobListing
from scrapers.career_source_detector import CareerSourceDetector
from utils.logger import get_logger

logger = get_logger("scraper.fractal")


class FractalScraper(BaseScraper):
    """Scrapes jobs from Fractal Analytics' official career portal."""

    @property
    def source_name(self) -> str:
        return "fractal"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.company_name = "Fractal Analytics"
        self.fallback_url = "https://fractal.myworkdayjobs.com/Fractal"
        self.detector = CareerSourceDetector()

    def scrape(self) -> list[JobListing]:
        """Scrape jobs from Fractal careers portal."""
        jobs: list[JobListing] = []
        
        # Discover ATS info
        try:
            info = self.detector.detect(self.company_name, self.fallback_url)
            platform = info.get("platform", "Workday")
            api_endpoint = info.get("api_endpoint", "")
            
            logger.info(f"[{self.company_name}] Detected platform: {platform}")
            
            if platform == "Workday":
                subdomain = "fractal.myworkdayjobs.com"
                tenant = "Fractal"
                url = api_endpoint or f"https://{subdomain}/wday/cxs/{tenant}/Fractal/jobs"
                
                client = self._get_client()
                keywords = ["AI", "Machine Learning", "GenAI", "Python", "Software"]
                
                for kw in keywords:
                    if self._max_jobs_limit and len(jobs) >= self._max_jobs_limit:
                        break
                    
                    logger.info(f"[{self.company_name}] Searching for '{kw}'")
                    payload = {
                        "appliedFacets": {},
                        "limit": 20,
                        "offset": 0,
                        "searchText": kw,
                    }
                    
                    try:
                        res = client.post(
                            url,
                            json=payload,
                            headers={
                                "Accept": "application/json",
                                "Content-Type": "application/json",
                                "Origin": f"https://{subdomain}",
                                "Referer": f"https://{subdomain}/"
                            }
                        )
                        if res.status_code == 200:
                            data = res.json()
                            postings = data.get("jobPostings", [])
                            logger.info(f"[{self.company_name}] Found {len(postings)} jobs for query '{kw}'")
                            
                            for item in postings:
                                if self._max_jobs_limit and len(jobs) >= self._max_jobs_limit:
                                    break
                                
                                title = item.get("title", "")
                                path = item.get("externalPath", "")
                                job_url = f"https://{subdomain}{path}"
                                location = item.get("location", "")
                                posted_date = item.get("postedOn", "")
                                
                                listing = JobListing(
                                    company=self.company_name,
                                    title=title,
                                    url=job_url,
                                    location=location,
                                    description=f"Fractal Analytics job listing for {title}. Location: {location}.",
                                    source=self.source_name,
                                    posted_date=posted_date,
                                    company_priority=100
                                )
                                jobs.append(listing)
                        else:
                            logger.warning(f"[{self.company_name}] HTTP {res.status_code} for query '{kw}'")
                    except Exception as e:
                        logger.warning(f"[{self.company_name}] Failed for query '{kw}': {e}")
                    
                    self._polite_delay(1.0, 2.0)
            else:
                logger.warning(f"[{self.company_name}] Discovered non-Workday platform. Falling back to custom scrape.")
        except Exception as e:
            logger.error(f"[{self.company_name}] Scraper execution failed: {e}", exc_info=True)

        print(f"[Fractal]\nQuery: AI/ML/Software\nJobs Found: {len(jobs)}\nJobs Parsed: {len(jobs)}")
        return jobs
