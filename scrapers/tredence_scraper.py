"""
Tredence Job Scraper.

Uses Playwright to fetch the RippleHire careers page and parses job listings.
"""

from scrapers.base_scraper import BaseScraper, JobListing
from scrapers.career_source_detector import CareerSourceDetector
from utils.logger import get_logger
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import re

logger = get_logger("scraper.tredence")


class TredenceScraper(BaseScraper):
    """Scrapes jobs from Tredence's RippleHire careers portal."""

    @property
    def source_name(self) -> str:
        return "tredence"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.company_name = "Tredence"
        self.fallback_url = "https://tredence.ripplehire.com/candidate"
        self.detector = CareerSourceDetector()

    def scrape(self) -> list[JobListing]:
        """Scrape jobs from Tredence careers portal."""
        jobs: list[JobListing] = []
        logger.info(f"[{self.company_name}] Running Tredence RippleHire scraper...")

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
            
            # Wait for jobs or links to render
            page.wait_for_timeout(5000) # Give it 5s to fully load React/Angular app
            html = page.content()
            context.close()
            if local_playwright:
                browser.close()
                local_playwright.stop()

            # 2. Parse HTML
            soup = BeautifulSoup(html, "lxml")
            
            # RippleHire usually lists jobs inside tables, rows or cards
            # We can find all links containing job details
            links = soup.find_all("a", href=re.compile(r"/job/detail|/job-detail|/job/", re.IGNORECASE))
            logger.info(f"[{self.company_name}] Found {len(links)} job links in DOM")

            seen_urls = set()
            for link in links:
                try:
                    job_url = link.get("href", "")
                    if not job_url:
                        continue
                    if not job_url.startswith("http"):
                        job_url = f"https://tredence.ripplehire.com{job_url}"
                        
                    if job_url in seen_urls:
                        continue
                    seen_urls.add(job_url)

                    # Get title
                    title = link.get_text(strip=True)
                    if not title or len(title) < 5 or any(x in title.lower() for x in ["read more", "view", "apply"]):
                        # Try to find header nearby
                        parent = link.parent
                        header = parent.find(["h1", "h2", "h3", "h4", "h5", "div"])
                        if header:
                            title = header.get_text(strip=True)
                    
                    if not title or len(title) < 3:
                        title = "Software Engineer / AI Specialist"

                    # Location (try to find location text in parent hierarchy)
                    location = "India"
                    parent = link.parent
                    for _ in range(4):
                        if parent is None:
                            break
                        text = parent.get_text(" ", strip=True)
                        # Look for common Indian cities
                        cities = ["Bengaluru", "Bangalore", "Chennai", "Pune", "Mumbai", "Gurugram", "Noida", "Hyderabad"]
                        found_cities = [c for c in cities if c.lower() in text.lower()]
                        if found_cities:
                            location = f"{found_cities[0]}, India"
                            break
                        parent = parent.parent

                    listing = JobListing(
                        company=self.company_name,
                        title=title,
                        url=job_url,
                        location=location,
                        description=f"Tredence RippleHire job: {title}. Location: {location}.",
                        source=self.source_name,
                        posted_date="Just now",
                        company_priority=95
                    )
                    jobs.append(listing)
                except Exception as e:
                    logger.debug(f"Error parsing link: {e}")
                    continue

        except Exception as e:
            logger.error(f"[{self.company_name}] RippleHire scraper failed: {e}", exc_info=True)

        print(f"[Tredence]\nQuery: ripplehire\nJobs Found: {len(jobs)}\nJobs Parsed: {len(jobs)}")
        return jobs
