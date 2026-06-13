"""
Tiger Analytics Job Scraper.

Uses CareerSourceDetector to identify platform and queries/scrapes Workable API or parses careers HTML.
"""

from scrapers.base_scraper import BaseScraper, JobListing
from scrapers.career_source_detector import CareerSourceDetector
from utils.logger import get_logger
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

logger = get_logger("scraper.tiger")


class TigerScraper(BaseScraper):
    """Scrapes jobs from Tiger Analytics' official career portal."""

    @property
    def source_name(self) -> str:
        return "tiger"

    def __init__(self, **kwargs) -> None:
        super().__init__(**kwargs)
        self.company_name = "Tiger Analytics"
        self.fallback_url = "https://apply.workable.com/tiger-analytics"
        self.detector = CareerSourceDetector()

    def _scrape_workable_api(self) -> list[JobListing]:
        """Query Workable API directly for speed and reliability."""
        jobs: list[JobListing] = []
        url = "https://apply.workable.com/api/v3/accounts/tiger-analytics/jobs"
        client = self._get_client()
        payload = {
            "query": "",
            "location": [],
            "department": [],
            "worktype": []
        }
        
        try:
            res = client.post(
                url,
                json=payload,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json"
                }
            )
            if res.status_code == 200:
                data = res.json()
                results = data.get("results", [])
                logger.info(f"[Tiger Analytics] Workable API returned {len(results)} jobs")
                
                for item in results:
                    title = item.get("title", "")
                    shortcode = item.get("shortcode", "")
                    job_url = f"https://apply.workable.com/tiger-analytics/j/{shortcode}/"
                    
                    # Location formatting
                    loc_data = item.get("location", {})
                    city = loc_data.get("city", "")
                    country = loc_data.get("country", "")
                    location = f"{city}, {country}" if city and country else (city or country or "India")
                    
                    posted_date = item.get("published", "")
                    
                    listing = JobListing(
                        company=self.company_name,
                        title=title,
                        url=job_url,
                        location=location,
                        description=f"Tiger Analytics job: {title}. Location: {location}.",
                        source=self.source_name,
                        posted_date=posted_date,
                        company_priority=95
                    )
                    jobs.append(listing)
            else:
                logger.warning(f"[Tiger Analytics] Workable API returned status {res.status_code}")
        except Exception as e:
            logger.warning(f"[Tiger Analytics] Workable API request failed: {e}")
            
        return jobs

    def _scrape_fallback_html(self) -> list[JobListing]:
        """Fallback Playwright scraper parsing the Workable page HTML."""
        jobs: list[JobListing] = []
        logger.info(f"[Tiger Analytics] Running Playwright fallback scraper...")
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 800}
                )
                page = context.new_page()
                page.goto(self.fallback_url, timeout=30000)
                
                # Wait for job listings to load
                page.wait_for_selector("[class*='job-item']", timeout=15000)
                html = page.content()
                browser.close()
                
            soup = BeautifulSoup(html, "lxml")
            cards = soup.select("[class*='job-item']") or soup.select(".job-item") or soup.select("li[class*='JobCard']")
            logger.info(f"[Tiger Analytics] Playwright page parsing found {len(cards)} cards")
            
            for card in cards:
                title_elem = card.select_one("h3") or card.select_one("[class*='title']")
                if not title_elem:
                    continue
                
                title = title_elem.get_text(strip=True)
                
                link_elem = card.select_one("a") or title_elem.select_one("a")
                job_url = link_elem.get("href", "") if link_elem else ""
                if job_url and not job_url.startswith("http"):
                    job_url = f"https://apply.workable.com{job_url}"
                
                loc_elem = card.select_one("[data-ui='job-location']") or card.select_one("[class*='location']")
                location = loc_elem.get_text(strip=True) if loc_elem else "India"
                
                posted_elem = card.select_one("[data-ui='job-published']") or card.select_one("[class*='published']")
                posted_date = posted_elem.get_text(strip=True) if posted_elem else ""
                
                listing = JobListing(
                    company=self.company_name,
                    title=title,
                    url=job_url,
                    location=location,
                    description=f"Tiger Analytics job listing: {title}. Location: {location}.",
                    source=self.source_name,
                    posted_date=posted_date,
                    company_priority=95
                )
                jobs.append(listing)
        except Exception as e:
            logger.error(f"[Tiger Analytics] Playwright fallback failed: {e}")
            
        return jobs

    def scrape(self) -> list[JobListing]:
        """Scrape jobs from Tiger Analytics."""
        # Try API first
        jobs = self._scrape_workable_api()
        if not jobs:
            # Fallback to HTML scraping
            jobs = self._scrape_fallback_html()
            
        print(f"[Tiger]\nQuery: workable\nJobs Found: {len(jobs)}\nJobs Parsed: {len(jobs)}")
        return jobs
