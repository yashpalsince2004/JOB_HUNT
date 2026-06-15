"""
LatentView Analytics Job Scraper.

Uses Playwright to fetch the LatentView careers page and parses job openings.
"""

from scrapers.base_scraper import BaseScraper, JobListing
from scrapers.career_source_detector import CareerSourceDetector
from utils.logger import get_logger
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import re

logger = get_logger("scraper.latentview")


class LatentviewScraper(BaseScraper):
    """Scrapes jobs from LatentView Analytics' official careers portal."""

    @property
    def source_name(self) -> str:
        return "latentview"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.company_name = "LatentView Analytics"
        self.fallback_url = "https://www.latentview.com/careers/"
        self.detector = CareerSourceDetector()

    def scrape(self) -> list[JobListing]:
        """Scrape jobs from LatentView careers portal."""
        jobs: list[JobListing] = []
        logger.info(f"[{self.company_name}] Running LatentView careers scraper...")

        browser = self._browser
        local_playwright = None
        
        try:
            if not browser:
                from playwright.sync_api import sync_playwright
                local_playwright = sync_playwright().start()
                browser = local_playwright.chromium.launch(headless=True)
            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
            page = context.new_page()
            
            # Stealth script features
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            page.add_init_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")
            page.add_init_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
            
            page.goto(self.fallback_url, timeout=30000)
            
            # Wait for any job list elements or wait a few seconds
            page.wait_for_timeout(5000)
            html = page.content()
            context.close()
            if local_playwright:
                browser.close()
                local_playwright.stop()

            soup = BeautifulSoup(html, "lxml")
            
            # LatentView jobs list typically has links matching jobs or position pages
            links = soup.find_all("a", href=re.compile(r"/careers/|/jobs/|/job-", re.IGNORECASE))
            logger.info(f"[{self.company_name}] Found {len(links)} candidate job links in DOM")

            seen_urls = set()
            for link in links:
                try:
                    job_url = link.get("href", "")
                    if not job_url:
                        continue
                    if not job_url.startswith("http"):
                        job_url = f"https://www.latentview.com{job_url}"
                        
                    # Skip common generic career/contact pages
                    url_lower = job_url.lower()
                    if any(x in url_lower for x in ["/culture", "/life-at", "/our-people", "/diversity", "/benefits", "/teams"]):
                        continue
                        
                    if job_url in seen_urls:
                        continue
                    seen_urls.add(job_url)

                    # Get title
                    title = link.get_text(strip=True)
                    if not title or len(title) < 5 or any(x in title.lower() for x in ["read more", "view", "apply", "careers", "job"]):
                        # Try to find header nearby
                        parent = link.parent
                        header = parent.find(["h1", "h2", "h3", "h4", "h5", "div"])
                        if header:
                            title = header.get_text(strip=True)
                    
                    if not title or len(title) < 3:
                        title = "Data Analyst / Analytics Engineer"

                    # Location
                    location = "India"
                    parent = link.parent
                    for _ in range(4):
                        if parent is None:
                            break
                        text = parent.get_text(" ", strip=True)
                        cities = ["Chennai", "Bengaluru", "Bangalore", "Mumbai", "Pune", "San Jose", "Princeton"]
                        found_cities = [c for c in cities if c.lower() in text.lower()]
                        if found_cities:
                            location = f"{found_cities[0]}, India" if found_cities[0] not in ["San Jose", "Princeton"] else f"{found_cities[0]}, USA"
                            break
                        parent = parent.parent

                    listing = JobListing(
                        company=self.company_name,
                        title=title,
                        url=job_url,
                        location=location,
                        description=f"LatentView Analytics career: {title}. Location: {location}.",
                        source=self.source_name,
                        posted_date="Just now",
                        company_priority=95
                    )
                    jobs.append(listing)
                except Exception as e:
                    logger.debug(f"Error parsing LatentView job link: {e}")
                    continue

        except Exception as e:
            logger.error(f"[{self.company_name}] Scraper failed: {e}", exc_info=True)

        print(f"[LatentView]\nQuery: careers\nJobs Found: {len(jobs)}\nJobs Parsed: {len(jobs)}")
        return jobs
