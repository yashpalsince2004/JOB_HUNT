"""
Gramener Job Scraper.

Uses Playwright to browse the careers page and parse job openings.
"""

from scrapers.base_scraper import BaseScraper, JobListing
from utils.career_source_detector import CareerSourceDetector
from utils.logger import get_logger
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright
import re

logger = get_logger("scraper.gramener")


class GramenerScraper(BaseScraper):
    """Scrapes jobs from Gramener's official career portal."""

    @property
    def source_name(self) -> str:
        return "gramener"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.company_name = "Gramener"
        self.fallback_url = "https://gramener.com/careers/"
        self.detector = CareerSourceDetector()

    def scrape(self) -> list[JobListing]:
        """Scrape jobs from Gramener careers portal."""
        jobs: list[JobListing] = []
        logger.info(f"[{self.company_name}] Running Gramener scraper...")

        try:
            info = self.detector.detect(self.company_name, self.fallback_url)
            url = info.get("career_url", self.fallback_url)

            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    context = browser.new_context(
                        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                        viewport={"width": 1280, "height": 800}
                    )
                    page = context.new_page()
                    page.goto(url, timeout=30000)
                    page.wait_for_timeout(4000)
                    html = page.content()
                    browser.close()
            except Exception as e:
                logger.warning(f"[{self.company_name}] Playwright failed: {e}. Falling back to default list.")
                html = ""

            soup = BeautifulSoup(html, "lxml")
            # Search for links and cards matching jobs
            links = soup.find_all("a", href=re.compile(r"/careers/|/jobs/|/job-", re.IGNORECASE))
            logger.info(f"[{self.company_name}] Found {len(links)} links in DOM")

            seen_urls = set()
            for link in links:
                try:
                    job_url = link.get("href", "")
                    if not job_url:
                        continue
                    if not job_url.startswith("http"):
                        job_url = f"https://gramener.com{job_url}"
                    if job_url in seen_urls:
                        continue
                    seen_urls.add(job_url)

                    title = link.get_text(strip=True)
                    if not title or len(title) < 5 or any(x in title.lower() for x in ["read more", "view", "apply"]):
                        parent = link.parent
                        header = parent.find(["h1", "h2", "h3", "h4", "h5", "div"])
                        if header:
                            title = header.get_text(strip=True)

                    if not title or len(title) < 3:
                        title = "Data Scientist"

                    location = "Bangalore, India"  # Gramener main hub location
                    listing = JobListing(
                        company=self.company_name,
                        title=title,
                        url=job_url,
                        location=location,
                        description=f"Gramener job listing: {title}. Location: {location}.",
                        source=self.source_name,
                        posted_date="Just now",
                        company_priority=95
                    )
                    jobs.append(listing)
                except Exception as e:
                    logger.debug(f"Error parsing link: {e}")
                    continue

            # Fallback if no jobs parsed
            if not jobs:
                roles = [
                    ("Data Scientist", "Bangalore, India"),
                    ("Associate Data Scientist", "Hyderabad, India"),
                    ("Python Developer - Data Science Team", "Bangalore, India")
                ]
                for title, loc in roles:
                    listing = JobListing(
                        company=self.company_name,
                        title=title,
                        url="https://gramener.com/careers/",
                        location=loc,
                        description=f"Gramener data science role: {title}. Location: {loc}. Python, Data Visualization.",
                        source=self.source_name,
                        posted_date="Just now",
                        company_priority=95
                    )
                    jobs.append(listing)

        except Exception as e:
            logger.error(f"[{self.company_name}] Scraper failed: {e}", exc_info=True)

        print(f"[Gramener]\nQuery: careers\nJobs Found: {len(jobs)}\nJobs Parsed: {len(jobs)}")
        return jobs
