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
    InstahyreScraper,
    HiristScraper,
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
        playwright_headless = settings.playwright_headless
        chrome_executable_path = settings.chrome_executable_path or None

        scraper_classes = [
            ("greenhouse", GreenhouseScraper),
            ("lever", LeverScraper),
            ("ashby", AshbyScraper),
            ("smartrecruiters", SmartRecruitersScraper),
            ("indeed", IndeedScraper),
            ("wellfound", WellfoundScraper),
            ("workday", WorkdayScraper),
            ("naukri", NaukriScraper),
            ("cutshort", CutshortScraper),
            ("foundit", FounditScraper),
            ("internshala", InternshalaScraper),
            ("quantiphi", QuantiphiScraper),
            ("fractal", FractalScraper),
            ("tiger", TigerScraper),
            ("tredence", TredenceScraper),
            ("latentview", LatentviewScraper),
            ("musigma", MusigmaScraper),
            ("nielseniq", NielseniqScraper),
            ("course5", Course5Scraper),
            ("gramener", GramenerScraper),
            ("exl", ExlScraper),
            ("talentd", TalentdScraper),
            ("instahyre", InstahyreScraper),
            ("hirist", HiristScraper),
        ]

        import os
        selected_scrapers_str = os.environ.get("SCRAPERS")
        if selected_scrapers_str:
            selected_names = [name.strip().lower() for name in selected_scrapers_str.split(",") if name.strip()]
            scraper_classes = [item for item in scraper_classes if item[0] in selected_names]
            self.logger.info(f"Filtered scrapers to run: {[name for name, _ in scraper_classes]}")

        all_listings: list[JobListing] = []

        # Indian job boards (Naukri, Foundit, Cutshort, Instahyre, Hirist) actively
        # detect and block headless Chromium. They must always run non-headless.
        ALWAYS_VISIBLE_SCRAPERS = {"naukri", "foundit", "cutshort", "instahyre", "hirist"}

        # Split scrapers into two groups by headless compatibility
        headless_scrapers = [(n, cls) for n, cls in scraper_classes if n not in ALWAYS_VISIBLE_SCRAPERS]
        visible_scrapers  = [(n, cls) for n, cls in scraper_classes if n in ALWAYS_VISIBLE_SCRAPERS]

        from playwright.sync_api import sync_playwright

        def _run_scraper_group(
            p,
            group: list,
            headless: bool,
            executable_path: str | None = None,
        ) -> list[JobListing]:
            """Launch one browser for a group and run all scrapers in it."""
            results: list[JobListing] = []
            if not group:
                return results
            self.logger.info(
                f"Initializing shared Playwright browser "
                f"(headless={headless}) for: {[n for n, _ in group]}"
            )
            try:
                launch_kwargs: dict = {
                    "headless": headless,
                    "args": ["--disable-blink-features=AutomationControlled"],
                }
                if executable_path:
                    launch_kwargs["executable_path"] = executable_path
                    self.logger.info(f"Using Chrome binary: {executable_path}")
                browser = p.chromium.launch(**launch_kwargs)
                for name, cls in group:
                    scraper = cls(max_jobs_limit=limit, browser=browser)
                    self.logger.info(f"Running scraper: {scraper.source_name}")
                    try:
                        with scraper:
                            listings = scraper.scrape()
                            results.extend(listings)
                            self.logger.info(
                                f"Scraper '{scraper.source_name}' completed: "
                                f"found {len(listings)} listings."
                            )
                    except Exception as e:
                        self.logger.error(
                            f"Scraper '{scraper.source_name}' failed: {e}",
                            exc_info=True,
                        )
                browser.close()
            except Exception as e:
                self.logger.error(
                    f"Playwright browser group (headless={headless}) failed: {e}",
                    exc_info=True,
                )
            return results

        try:
            with sync_playwright() as p:
                # 1. Headless browser for API-based / bot-tolerant scrapers
                all_listings.extend(_run_scraper_group(p, headless_scrapers, headless=playwright_headless))

                # 2. Non-headless browser for Indian job boards that block headless.
                # Uses system Chrome to avoid SIGBUS crash with Playwright's bundled Chromium.
                if visible_scrapers:
                    all_listings.extend(
                        _run_scraper_group(
                            p,
                            visible_scrapers,
                            headless=False,
                            executable_path=chrome_executable_path,
                        )
                    )
        except Exception as e:
            self.logger.error(f"Playwright execution context failed: {e}", exc_info=True)

        self.logger.info(f"All scrapers completed. Total listings: {len(all_listings)}")
        return all_listings
