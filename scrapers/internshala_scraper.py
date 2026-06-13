"""
Internshala job and fresher role scraper using Playwright.

Queries Internshala, filters out unpaid, marketing, and sales roles,
extracts job details, and returns JobListing objects.
"""

import urllib.parse
import re
from typing import Any
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from scrapers.base_scraper import BaseScraper, JobListing
from utils.logger import get_logger

logger = get_logger("scraper.internshala")


class InternshalaScraper(BaseScraper):
    """Scrapes jobs from Internshala using Playwright."""

    @property
    def source_name(self) -> str:
        return "internshala"

    def __init__(self, queries: list[str] | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._queries = queries or [
            "ai",
            "machine-learning",
            "python",
            "android",
            "flutter"
        ]

    def _normalize_salary(self, salary_str: str) -> tuple[float, float, str, str]:
        if not salary_str or "unpaid" in salary_str.lower() or "no stipend" in salary_str.lower() or "no salary" in salary_str.lower():
            return 0.0, 0.0, "INR", "monthly"
            
        salary_clean = salary_str.lower().replace(",", "").replace(" ", "").replace("/month", "").replace("/year", "")
        currency = "INR"
        if "$" in salary_clean or "usd" in salary_clean:
            currency = "USD"
            
        period = "monthly"
        if "year" in salary_str.lower() or "lpa" in salary_str.lower() or "annual" in salary_str.lower():
            period = "yearly"
            
        numbers = re.findall(r"\d+\.?\d*", salary_clean)
        if not numbers:
            return 0.0, 0.0, currency, period
            
        is_lpa = "lpa" in salary_clean or "lakh" in salary_clean or "lac" in salary_clean
        
        val_min = float(numbers[0])
        val_max = float(numbers[1]) if len(numbers) > 1 else val_min
        
        if is_lpa:
            val_min *= 100000
            val_max *= 100000
            period = "yearly"
        elif val_min < 100 and currency == "INR":
            # Likely LPA
            val_min *= 100000
            val_max *= 100000
            period = "yearly"
            
        return val_min, val_max, currency, period

    def _should_ignore(self, title: str, salary: str) -> tuple[bool, str]:
        """Check if role should be ignored based on Internshala rules."""
        title_lower = title.lower()
        sal_lower = salary.lower() if salary else ""
        
        # 1. Unpaid check
        if any(w in sal_lower for w in ["unpaid", "no stipend", "no salary", "0 stipend"]):
            return True, "unpaid"
            
        # 2. Marketing / Sales / Business Development check
        ignore_words = ["marketing", "sales", "business development", "social media", "hr ", "human resource", "content writing", "graphic design", "seo "]
        for word in ignore_words:
            if word in title_lower:
                return True, f"contains ignore word: '{word}'"
                
        return False, ""

    def _scrape_query(self, query: str, limit: int = 50) -> list[JobListing]:
        jobs: list[JobListing] = []
        encoded_query = urllib.parse.quote_plus(query)
        # Internshala URL structure
        url = f"https://internshala.com/jobs/keywords-{encoded_query}"
        
        logger.info(f"[Internshala] Query: '{query}' searching...")
        
        try:
            with sync_playwright() as p:
                browser = p.chromium.launch(headless=True)
                context = browser.new_context(
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                    viewport={"width": 1280, "height": 800}
                )
                page = context.new_page()
                page.goto(url, timeout=30000)
                
                # Wait for internship/job containers
                page.wait_for_selector(".individual_internship", timeout=15000)
                
                # Scroll
                page.evaluate("window.scrollTo(0, document.body.scrollHeight/3)")
                page.wait_for_timeout(2000)
                
                html = page.content()
                browser.close()
        except Exception as e:
            logger.warning(f"[Internshala] Playwright failed for query '{query}': {e}")
            print(f"[Internshala]\nQuery: {query}\nJobs Found: 0\nJobs Parsed: 0")
            return []

        soup = BeautifulSoup(html, "lxml")
        cards = soup.select(".individual_internship")
        
        jobs_found = len(cards)
        jobs_parsed = 0
        
        for card in cards:
            if len(jobs) >= limit:
                break
            try:
                # 1. Title and URL
                title_elem = card.select_one(".job-title-container") or card.select_one(".heading_4_5 a") or card.select_one("a")
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)
                
                # Link
                link_elem = card.select_one(".heading_4_5 a") or card.select_one("a")
                job_url = link_elem.get("href", "") if link_elem else ""
                if job_url and not job_url.startswith("http"):
                    job_url = f"https://internshala.com{job_url}"
                if not job_url:
                    continue
                
                # 2. Company
                company_elem = card.select_one(".company_name") or card.select_one("a.link_display_like_text")
                company = company_elem.get_text(strip=True) if company_elem else "Unknown"
                
                # 3. Location & Remote
                location_elem = card.select_one(".location_link") or card.select_one("#location_names")
                location = location_elem.get_text(strip=True) if location_elem else "India"
                
                remote_status = "onsite"
                loc_lower = location.lower()
                if "work from home" in loc_lower or "remote" in loc_lower:
                    remote_status = "remote"
                elif "hybrid" in loc_lower:
                    remote_status = "hybrid"
                
                # 4. Salary/Stipend
                sal_elem = card.select_one(".salary_container") or card.select_one(".stipend_container") or card.select_one(".stipend")
                salary = sal_elem.get_text(strip=True) if sal_elem else ""
                
                # Filter out unpaid / sales / marketing
                should_ignore, ignore_reason = self._should_ignore(title, salary)
                if should_ignore:
                    logger.debug(f"Ignoring Internshala job '{title}' because: {ignore_reason}")
                    continue
                
                sal_min, sal_max, sal_curr, sal_per = self._normalize_salary(salary)
                
                # 5. Experience
                # Internshala jobs sometimes list experience, but internships are typically 0 years
                exp_elem = card.select_one(".experience") or card.select_one(".job-experience")
                experience = exp_elem.get_text(strip=True) if exp_elem else "0-1 years"
                
                # 6. Description / Skills
                # Internshala cards don't show full descriptions, but we can combine details
                skills_elems = card.select(".skill-tag")
                skills = [s.get_text(strip=True) for s in skills_elems]
                skills_str = ", ".join(skills)
                
                # Description
                description = f"Fresher job at {company} in {location}. Salary/Stipend: {salary}. Skills: {skills_str}"
                
                # 7. Posted Date
                posted_elem = card.select_one(".status-container") or card.select_one(".posted")
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
                logger.debug(f"Error parsing Internshala card: {e}")
                continue

        print(f"[Internshala]\nQuery: {query}\nJobs Found: {jobs_found}\nJobs Parsed: {jobs_parsed}")
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

        logger.info(f"[Internshala] Finished. Total scraped: {len(all_jobs)}")
        return all_jobs
