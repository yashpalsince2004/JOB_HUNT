"""
Deduplication Agent.

Filters out jobs that have already been scraped or applied to.
Uses Google Sheets client if initialized, otherwise falls back to a local set.
"""

import urllib.parse
from typing import Any

from agents.base_agent import BaseAgent
from scrapers.base_scraper import JobListing
from sheets.client import SheetsClient


class DedupAgent(BaseAgent):
    """Filters duplicate job listings based on URL normalization and job_id hashes."""

    @property
    def name(self) -> str:
        return "dedup"

    def __init__(self, sheets_client: SheetsClient | None = None) -> None:
        super().__init__()
        self._sheets_client = sheets_client

    def _normalize_url(self, url: str) -> str:
        """Remove tracking parameters and query strings from a URL."""
        if not url:
            return ""
        parsed = urllib.parse.urlparse(url)
        # Reconstruct URL without query and fragment parameters
        normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
        return normalized.strip().lower()

    def run(self, listings: list[JobListing]) -> list[JobListing]:
        """
        Deduplicate listings against Google Sheets.

        Args:
            listings: List of newly scraped JobListing objects.

        Returns:
            Filtered list of JobListing objects.
        """
        existing_urls: set[str] = set()
        existing_ids: set[str] = set()

        if self._sheets_client:
            try:
                self.logger.info("Fetching existing jobs from Google Sheets...")
                existing_urls = {self._normalize_url(u) for u in self._sheets_client.get_all_job_urls()}
                existing_ids = self._sheets_client.get_all_job_ids()
                self.logger.info(
                    f"Loaded {len(existing_urls)} URLs and {len(existing_ids)} IDs "
                    "from Google Sheets."
                )
            except Exception as e:
                self.logger.warning(
                    f"Failed to fetch from Google Sheets: {e}. "
                    "Proceeding with local deduplication only."
                )

        unique_listings: list[JobListing] = []
        seen_in_run_urls: set[str] = set()
        seen_in_run_ids: set[str] = set()

        for listing in listings:
            norm_url = self._normalize_url(listing.url)
            job_id = listing.job_id

            # Check if duplicate in current run
            if norm_url in seen_in_run_urls or job_id in seen_in_run_ids:
                continue

            # Check if duplicate in Sheets
            if norm_url in existing_urls or job_id in existing_ids:
                continue

            # Keep it
            seen_in_run_urls.add(norm_url)
            seen_in_run_ids.add(job_id)
            unique_listings.append(listing)

        self.logger.info(
            f"Deduplication finished: {len(listings)} input -> "
            f"{len(unique_listings)} unique (filtered {len(listings) - len(unique_listings)} duplicates)"
        )
        return unique_listings
