"""
Indeed job board scraper.

Queries Indeed search results pages using browser-like headers.
Attempts to extract jobs for specific search queries.
Due to aggressive anti-bot measures, this scraper is designed to fail gracefully.
"""

import urllib.parse
from bs4 import BeautifulSoup

from config.companies import INDEED_SEARCH_QUERIES
from scrapers.base_scraper import BaseScraper, JobListing
from utils.logger import get_logger

logger = get_logger("scraper.indeed")


class IndeedScraper(BaseScraper):
    """Scrapes jobs from Indeed India using search queries."""

    @property
    def source_name(self) -> str:
        return "indeed"

    def __init__(self, queries: list[str] | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._queries = queries or INDEED_SEARCH_QUERIES

    def _scrape_query(self, query: str, limit: int | None = None) -> list[JobListing]:
        """Scrape jobs for a single query."""
        jobs: list[JobListing] = []
        encoded_query = urllib.parse.quote_plus(query)
        # Search Indeed India by default
        url = f"https://in.indeed.com/jobs?q={encoded_query}"

        logger.info(f"[Indeed] Searching for: {query}")
        html = self._get_html(url)

        soup = BeautifulSoup(html, "lxml")
        
        # Indeed job cards typically have class "job_seen_beacon" or similar
        cards = soup.select(".job_seen_beacon")
        if not cards:
            # Fallback to older card class names
            cards = soup.select(".result")

        for card in cards:
            if limit is not None and len(jobs) >= limit:
                break
            try:
                # Extract Title
                title_elem = card.select_one("h2.jobTitle") or card.select_one("h2.title")
                if not title_elem:
                    continue
                title = title_elem.get_text(strip=True)
                
                # Extract URL
                link_elem = title_elem.select_one("a") or card.select_one("a.jcs-JobTitle")
                if not link_elem:
                    continue
                
                href_attr = link_elem.get("href")
                if not href_attr:
                    continue
                
                if isinstance(href_attr, list):
                    href = href_attr[0] if href_attr else ""
                else:
                    href = str(href_attr)
                
                href = href.strip()
                if href.startswith("/"):
                    job_url = f"https://in.indeed.com{href}"
                else:
                    job_url = href

                # Extract Company
                company_elem = card.select_one(".companyName") or card.select_one("[data-testid='company-name']")
                company = company_elem.get_text(strip=True) if company_elem else "Unknown"

                # Extract Location
                location_elem = card.select_one(".companyLocation") or card.select_one("[data-testid='text-location']")
                location = location_elem.get_text(strip=True) if location_elem else "India"

                # Extract snippet/description
                snippet_elem = card.select_one(".job-snippet") or card.select_one(".summary")
                description = snippet_elem.get_text(separator="\n", strip=True) if snippet_elem else ""

                # Indeed date
                date_elem = card.select_one(".date") or card.select_one("[data-testid='myJobsState-date']")
                posted_date = date_elem.get_text(strip=True) if date_elem else ""

                listing = JobListing(
                    company=company,
                    title=title,
                    url=job_url,
                    location=location,
                    description=description,
                    source=self.source_name,
                    posted_date=posted_date,
                )
                jobs.append(listing)
            except Exception as e:
                logger.debug(f"Error parsing Indeed card: {e}")
                continue

        logger.info(f"[Indeed] Query '{query}': found {len(jobs)} jobs")
        return jobs

    def scrape(self) -> list[JobListing]:
        """Run indeed scraping for all queries."""
        all_jobs: list[JobListing] = []

        for query in self._queries:
            if self._max_jobs_limit is not None and len(all_jobs) >= self._max_jobs_limit:
                break
            rem_limit = None
            if self._max_jobs_limit is not None:
                rem_limit = self._max_jobs_limit - len(all_jobs)
            try:
                jobs = self._scrape_query(query, limit=rem_limit)
                all_jobs.extend(jobs)
                self._polite_delay(3.0, 6.0)  # Indeed requires a larger delay to avoid blocking
            except Exception as e:
                logger.warning(f"[Indeed] Failed to scrape query '{query}': {e}")
                # If we detect 403 Forbidden blocking, abort the loop immediately
                if "403" in str(e) or "forbidden" in str(e).lower() or "blocked" in str(e).lower():
                    logger.error("[Indeed] Indeed is blocking requests (403 Forbidden). Aborting scraper run.")
                    break

        logger.info(f"[Indeed] Total: {len(all_jobs)} jobs from {len(self._queries)} queries")
        return all_jobs
