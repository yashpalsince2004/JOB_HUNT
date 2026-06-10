"""
Scraper Agent.

Orchestrates all individual scrapers, aggregates results, and handles
failures per-scraper to prevent a single scraper from failing the entire run.
"""

from typing import Any

from agents.base_agent import BaseAgent
from scrapers import (
    GreenhouseScraper,
    LeverScraper,
    AshbyScraper,
    SmartRecruitersScraper,
    IndeedScraper,
    WellfoundScraper,
    WorkdayScraper,
    JobListing,
)


class ScraperAgent(BaseAgent):
    """Orchestrates all scraping tasks across various job platforms."""

    @property
    def name(self) -> str:
        return "scraper"

    def run(self, input_data: Any = None) -> list[JobListing]:
        """
        Run all scrapers and aggregate results.

        Args:
            input_data: Unused.

        Returns:
            List of aggregated JobListing objects.
        """
        scrapers = [
            GreenhouseScraper(),
            LeverScraper(),
            AshbyScraper(),
            SmartRecruitersScraper(),
            IndeedScraper(),
            WellfoundScraper(),
            WorkdayScraper(),
        ]

        all_listings: list[JobListing] = []

        for scraper in scrapers:
            self.logger.info(f"Running scraper: {scraper.source_name}")
            try:
                with scraper:
                    listings = scraper.scrape()
                    all_listings.extend(listings)
                    self.logger.info(
                        f"Scraper '{scraper.source_name}' completed: "
                        f"found {len(listings)} listings."
                    )
            except Exception as e:
                self.logger.error(
                    f"Scraper '{scraper.source_name}' failed: {e}",
                    exc_info=True
                )
                # Keep going if one scraper fails

        self.logger.info(f"All scrapers completed. Total listings: {len(all_listings)}")
        return all_listings
