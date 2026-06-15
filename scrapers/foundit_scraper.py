"""
Foundit India job scraper using Playwright.

Queries Foundit.in (formerly Monster India), extracts job details,
performs normalization, and returns JobListing objects.
"""

import urllib.parse
import re
from typing import Any
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from scrapers.base_scraper import BaseScraper, JobListing
from utils.logger import get_logger

logger = get_logger("scraper.foundit")


class FounditScraper(BaseScraper):
    """Scrapes jobs from Foundit.in using Playwright."""

    @property
    def source_name(self) -> str:
        return "foundit"

    def __init__(self, queries: list[str] | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._queries = queries or [
            "AI",
            "Data Science",
            "Python",
            "Software Engineering"
        ]

    def _normalize_salary(self, salary_str: str) -> tuple[float, float, str, str]:
        if not salary_str or "unspecified" in salary_str.lower() or "not disclosed" in salary_str.lower():
            return 0.0, 0.0, "INR", "yearly"
        
        salary_clean = salary_str.lower().replace(",", "").replace(" ", "")
        currency = "INR"
        if "$" in salary_clean or "usd" in salary_clean:
            currency = "USD"
            
        period = "yearly"
        if "month" in salary_clean or "/pm" in salary_clean:
            period = "monthly"
            
        numbers = re.findall(r"\d+\.?\d*", salary_clean)
        if not numbers:
            return 0.0, 0.0, currency, period
            
        is_lpa = "lpa" in salary_clean or "lakh" in salary_clean or "lac" in salary_clean
        
        val_min = float(numbers[0])
        val_max = float(numbers[1]) if len(numbers) > 1 else val_min
        
        if is_lpa:
            val_min *= 100000
            val_max *= 100000
        elif val_min < 100 and currency == "INR":
            val_min *= 100000
            val_max *= 100000
            
        return val_min, val_max, currency, period

    def _extract_experience_years(self, exp_str: str) -> int | None:
        if not exp_str:
            return None
        exp_lower = exp_str.lower()
        numbers = re.findall(r"\d+", exp_lower)
        if not numbers:
            if "fresher" in exp_lower or "entry" in exp_lower:
                return 0
            return None
        return int(numbers[0])

    def _scrape_query(self, query: str, limit: int = 50) -> list[JobListing]:
        jobs: list[JobListing] = []
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://www.foundit.in/srp/results?query={encoded_query}"
        
        browser = self._browser
        local_playwright = None
        
        try:
            if not browser:
                from playwright.sync_api import sync_playwright
                local_playwright = sync_playwright().start()
                browser = local_playwright.chromium.launch(
                    headless=True,
                    args=["--disable-blink-features=AutomationControlled"]
                )

            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800}
            )
            page = context.new_page()
            
            # Stealth script features
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            page.add_init_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")
            page.add_init_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")
            
            page.goto(url, timeout=30000)
            
            # Foundit lists container/job cards wrapper
            page.wait_for_selector(".card-container", timeout=15000)
            
            # Scroll
            page.evaluate("window.scrollTo(0, document.body.scrollHeight/3)")
            page.wait_for_timeout(2000)
            
            html = page.content()
            
            context.close()
            if local_playwright:
                browser.close()
                local_playwright.stop()
        except Exception as e:
            logger.warning(f"[Foundit] Playwright failed for query '{query}': {e}")
            print(f"[Foundit]\nQuery: {query}\nJobs Found: 0\nJobs Parsed: 0")
            if local_playwright:
                try:
                    browser.close()
                except Exception:
                    pass
                local_playwright.stop()
            return []

        soup = BeautifulSoup(html, "lxml")
        cards = soup.select(".card-container") or soup.select("div[class*='cardContainer']") or soup.select(".job-card")
        
        jobs_found = len(cards)
        jobs_parsed = 0
        
        for card in cards:
            if len(jobs) >= limit:
                break
            try:
                # 1. Title and URL
                title_elem = card.select_one(".job-title") or card.select_one("h3") or card.select_one("a")
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)
                
                # Link
                link_elem = title_elem.select_one("a") or card.select_one("a")
                job_url = link_elem.get("href", "") if link_elem else ""
                if job_url and not job_url.startswith("http"):
                    job_url = f"https://www.foundit.in{job_url}"
                if not job_url:
                    continue
                
                # 2. Company
                company_elem = card.select_one(".company-name") or card.select_one("span.company")
                company = company_elem.get_text(strip=True) if company_elem else "Unknown"
                
                # 3. Location & Remote
                location_elem = card.select_one(".location") or card.select_one("span.location")
                location = location_elem.get_text(strip=True) if location_elem else "India"
                
                remote_status = "onsite"
                loc_lower = location.lower()
                if "remote" in loc_lower or "wfh" in loc_lower or "work from home" in loc_lower:
                    remote_status = "remote"
                elif "hybrid" in loc_lower:
                    remote_status = "hybrid"
                
                # 4. Experience
                exp_elem = card.select_one(".exp") or card.select_one(".experience") or card.select_one("span:contains('yrs')")
                experience = exp_elem.get_text(strip=True) if exp_elem else ""
                
                # 5. Salary
                sal_elem = card.select_one(".salary") or card.select_one("span:contains('LPA')")
                salary = sal_elem.get_text(strip=True) if sal_elem else ""
                sal_min, sal_max, sal_curr, sal_per = self._normalize_salary(salary)
                
                # 6. Skills
                skills = []
                skill_elems = card.select(".skill-tag") or card.select(".chip") or card.select(".badge")
                for s in skill_elems:
                    skills.append(s.get_text(strip=True))
                skills_str = ", ".join(skills)
                
                # 7. Description snippet
                desc_elem = card.select_one(".job-description") or card.select_one("div[class*='snippet']")
                description = desc_elem.get_text(strip=True) if desc_elem else ""
                
                # 8. Posted Date
                posted_elem = card.select_one(".posted-date") or card.select_one(".posted")
                posted_date = posted_elem.get_text(strip=True) if posted_elem else ""

                listing = JobListing(
                    company=company,
                    title=title,
                    url=job_url,
                    location=location,
                    description=description,
                    source=self.source_name,
                    posted_date=posted_date,
                    experience=experience,
                    salary=salary,
                    skills=skills_str,
                    remote_status=remote_status,
                    salary_min=sal_min,
                    salary_max=sal_max,
                    salary_currency=sal_curr,
                    salary_period=sal_per,
                )
                jobs.append(listing)
                jobs_parsed += 1
            except Exception as e:
                logger.debug(f"Error parsing Foundit job card: {e}")
                continue

        print(f"[Foundit]\nQuery: {query}\nJobs Found: {jobs_found}\nJobs Parsed: {jobs_parsed}")
        return jobs

    def scrape(self) -> list[JobListing]:
        all_jobs: list[JobListing] = []
        run_limit = self._max_jobs_limit or 150
        
        for query in self._queries:
            if len(all_jobs) >= run_limit:
                break
            query_limit = min(50, run_limit - len(all_jobs))
            jobs = self._scrape_query(query, limit=query_limit)
            all_jobs.extend(jobs)
            self._polite_delay(2.0, 4.0)

        logger.info(f"[Foundit] Finished. Total scraped: {len(all_jobs)}")
        return all_jobs
