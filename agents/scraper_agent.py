"""
Scraper Agent.

Orchestrates all individual scrapers, aggregates results, and handles
failures per-scraper to prevent a single scraper from failing the entire run.
"""

from typing import Any

from agents.base_agent import BaseAgent
from config.settings import Settings
from scrapers import (
    GreenhouseScraper,
    LeverScraper,
    AshbyScraper,
    SmartRecruitersScraper,
    IndeedScraper,
    WellfoundScraper,
    WorkdayScraper,
    NaukriScraper,
    CutshortScraper,
    FounditScraper,
    InternshalaScraper,
    QuantiphiScraper,
    FractalScraper,
    TigerScraper,
    TredenceScraper,
    LatentviewScraper,
    MusigmaScraper,
    NielseniqScraper,
    Course5Scraper,
    GramenerScraper,
    ExlScraper,
    TalentdScraper,
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
        settings = Settings()
        limit = settings.max_jobs_per_source

        scrapers = [
            GreenhouseScraper(max_jobs_limit=limit),
            LeverScraper(max_jobs_limit=limit),
            AshbyScraper(max_jobs_limit=limit),
            SmartRecruitersScraper(max_jobs_limit=limit),
            IndeedScraper(max_jobs_limit=limit),
            WellfoundScraper(max_jobs_limit=limit),
            WorkdayScraper(max_jobs_limit=limit),
            NaukriScraper(max_jobs_limit=limit),
            CutshortScraper(max_jobs_limit=limit),
            FounditScraper(max_jobs_limit=limit),
            InternshalaScraper(max_jobs_limit=limit),
            QuantiphiScraper(max_jobs_limit=limit),
            FractalScraper(max_jobs_limit=limit),
            TigerScraper(max_jobs_limit=limit),
            TredenceScraper(max_jobs_limit=limit),
            LatentviewScraper(max_jobs_limit=limit),
            MusigmaScraper(max_jobs_limit=limit),
            NielseniqScraper(max_jobs_limit=limit),
            Course5Scraper(max_jobs_limit=limit),
            GramenerScraper(max_jobs_limit=limit),
            ExlScraper(max_jobs_limit=limit),
            TalentdScraper(max_jobs_limit=limit),
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
