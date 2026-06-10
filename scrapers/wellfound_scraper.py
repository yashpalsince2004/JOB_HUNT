"""
Wellfound (formerly AngelList) job board scraper.

Attempts to scrape Wellfound startup job listings.
Wellfound heavily shields its platform behind Cloudflare; this scraper handles blocks gracefully.
"""

from scrapers.base_scraper import BaseScraper, JobListing
from utils.logger import get_logger

logger = get_logger("scraper.wellfound")


class WellfoundScraper(BaseScraper):
    """Scrapes jobs from Wellfound."""

    @property
    def source_name(self) -> str:
        return "wellfound"

    def scrape(self) -> list[JobListing]:
        """
        Scrape Wellfound jobs.
        Wellfound is heavily protected, so we return empty by default to prevent blocking the pipeline.
        """
        logger.info("[Wellfound] Wellfound scraping is disabled by default due to Cloudflare anti-bot protection.")
        return []
