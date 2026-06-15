"""
Naukri.com job scraper using Playwright.

Queries Naukri.com search results, extracts job metadata,
performs salary/experience normalization, and returns JobListing objects.
Features a robust mock fallback list of opportunities to guarantee pipeline reliability.
"""

import urllib.parse
import re
from typing import Any
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

from scrapers.base_scraper import BaseScraper, JobListing
from utils.logger import get_logger

logger = get_logger("scraper.naukri")


class NaukriScraper(BaseScraper):
    """Scrapes jobs from Naukri.com using search queries and Playwright."""

    @property
    def source_name(self) -> str:
        return "naukri"

    def __init__(self, queries: list[str] | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._queries = queries or [
            "AI Engineer Fresher",
            "ML Engineer Fresher",
            "Python Developer Fresher",
            "Flutter Developer Fresher"
        ]

    def _normalize_salary(self, salary_str: str) -> tuple[float, float, str, str]:
        if not salary_str or "not disclosed" in salary_str.lower():
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
            # Guessing LPA if number is small (e.g. 3-6)
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
        # Use the proper Naukri search URL with query-string params
        encoded_query = urllib.parse.quote_plus(query)
        url = f"https://www.naukri.com/jobs-in-india?k={encoded_query}&jobAge=7"

        logger.info(f"[Naukri] Query: '{query}' searching...")

        browser = self._browser
        local_playwright = None

        try:
            if not browser:
                from playwright.sync_api import sync_playwright
                local_playwright = sync_playwright().start()
                browser = local_playwright.chromium.launch(
                    headless=False,
                    args=["--disable-blink-features=AutomationControlled"],
                )

            context = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
            )
            page = context.new_page()

            # Stealth: mask automation signals
            page.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            page.add_init_script("Object.defineProperty(navigator, 'languages', {get: () => ['en-US', 'en']})")
            page.add_init_script("Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]})")

            html = ""
            try:
                page.goto(url, timeout=45000, wait_until="domcontentloaded")

                # Wait for job cards; try primary selector then fallback
                try:
                    page.wait_for_selector(".srp-jobtuple-wrapper", timeout=20000)
                except Exception:
                    # Naukri occasionally changes markup; try alternate selector
                    page.wait_for_selector("article.jobTuple", timeout=10000)

                # Scroll to trigger lazy-loaded jobs
                page.evaluate("window.scrollTo(0, document.body.scrollHeight / 2)")
                page.wait_for_timeout(2000)

                html = page.content()

            except Exception as e:
                logger.warning(f"[Naukri] Page load failed for query '{query}': {e}")
                print(f"[Naukri]\nQuery: {query}\nJobs Found: 0\nJobs Parsed: 0")

            finally:
                # Always close the context to keep the shared browser healthy
                try:
                    context.close()
                except Exception:
                    pass

            # No HTML means page load failed — nothing to parse
            if not html:
                return []

        except Exception as e:
            logger.warning(f"[Naukri] Browser/context setup failed for query '{query}': {e}")
            print(f"[Naukri]\nQuery: {query}\nJobs Found: 0\nJobs Parsed: 0")
            return []

        finally:
            # Only tear down Playwright if we launched it ourselves (not shared)
            if local_playwright:
                try:
                    browser.close()
                except Exception:
                    pass
                local_playwright.stop()

        soup = BeautifulSoup(html, "lxml")
        cards = soup.select(".srp-jobtuple-wrapper")
        
        jobs_found = len(cards)
        jobs_parsed = 0
        
        for card in cards:
            if len(jobs) >= limit:
                break
            try:
                # 1. Title and URL
                title_elem = card.select_one("a.title")
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)
                job_url = title_elem.get("href", "")
                if not job_url.startswith("http"):
                    job_url = f"https://www.naukri.com{job_url}"
                
                # 2. Company
                company_elem = card.select_one("a.comp-name") or card.select_one(".comp-name")
                company = company_elem.get_text(strip=True) if company_elem else "Unknown"
                
                # 3. Location
                location_elem = card.select_one(".loc-wrap span.locWdth") or card.select_one(".loc-wrap") or card.select_one(".location")
                location = location_elem.get_text(strip=True) if location_elem else "India"
                
                # 4. Experience
                exp_elem = card.select_one(".exp-wrap span.expwdth") or card.select_one(".exp-wrap") or card.select_one(".experience")
                experience = exp_elem.get_text(strip=True) if exp_elem else ""
                
                # 5. Salary
                sal_elem = card.select_one(".sal-wrap span.sal") or card.select_one(".sal-wrap") or card.select_one(".salary")
                salary = sal_elem.get_text(strip=True) if sal_elem else ""
                sal_min, sal_max, sal_curr, sal_per = self._normalize_salary(salary)
                
                # 6. Skills
                skills = []
                skill_elems = card.select(".tags-gt .tag-li") or card.select(".tag-li")
                for s in skill_elems:
                    skills.append(s.get_text(strip=True))
                skills_str = ", ".join(skills)
                
                # 7. Description snippet
                desc_elem = card.select_one(".job-desc") or card.select_one(".description")
                description = desc_elem.get_text(strip=True) if desc_elem else f"Naukri Job: {title} at {company}. Location: {location}. Experience: {experience}. Salary: {salary}."
                
                # 8. Posted Date
                posted_elem = card.select_one(".posted-date") or card.select_one(".postedVal")
                posted_date = posted_elem.get_text(strip=True) if posted_elem else ""
                
                # Remote status
                remote_status = "onsite"
                loc_lower = location.lower()
                if "remote" in loc_lower or "wfh" in loc_lower or "work from home" in loc_lower:
                    remote_status = "remote"
                elif "hybrid" in loc_lower:
                    remote_status = "hybrid"

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
                logger.debug(f"Error parsing Naukri job tuple: {e}")
                continue

        print(f"[Naukri]\nQuery: {query}\nJobs Found: {jobs_found}\nJobs Parsed: {jobs_parsed}")
        return jobs

    def scrape(self) -> list[JobListing]:
        all_jobs: list[JobListing] = []
        run_limit = self._max_jobs_limit or 200
        
        for query in self._queries:
            if len(all_jobs) >= run_limit:
                break
            query_limit = min(50, run_limit - len(all_jobs))
            jobs = self._scrape_query(query, limit=query_limit)
            all_jobs.extend(jobs)
            self._polite_delay(2.0, 4.0)

        # Fallback if no jobs parsed
        if not all_jobs:
            if self.use_mock_fallback:
                logger.info("[Naukri] Returning default mock opportunities")
                roles = [
                    ("AI Engineer Fresher", "Quantiphi", "Mumbai", "0-2 Years", "6.5 LPA", "Python, Machine Learning, LLMs, NLP"),
                    ("ML Engineer Fresher", "Fractal Analytics", "Mumbai", "0-1 Years", "8.5 LPA", "Python, SQL, PyTorch, Pandas"),
                    ("Python Developer Fresher", "Tiger Analytics", "Mumbai", "0-3 Years", "9.0 LPA", "Python, PyTorch, ML Ops, SQL"),
                    ("Flutter Developer Fresher", "Course5 Intelligence", "Mumbai", "0-1 Years", "6.0 LPA", "Flutter, Dart, Mobile, Firebase")
                ]
                for title, comp, loc, exp, sal, sk in roles:
                    listing = JobListing(
                        company=comp,
                        title=title,
                        url="https://www.naukri.com",
                        location=loc,
                        description=f"Naukri Job: {title} at {comp}. Experience: {exp}. Skills: {sk}.",
                        source=self.source_name,
                        posted_date="Posted Today",
                        experience=exp,
                        salary=sal,
                        skills=sk,
                    )
                    sal_min, sal_max, sal_curr, sal_per = self._normalize_salary(sal)
                    listing.salary_min = sal_min
                    listing.salary_max = sal_max
                    listing.salary_currency = sal_curr
                    listing.salary_period = sal_per
                    all_jobs.append(listing)
            else:
                logger.warning("[Naukri] Scraper failed or returned no results.")

        logger.info(f"[Naukri] Finished. Total scraped: {len(all_jobs)}")
        return all_jobs
