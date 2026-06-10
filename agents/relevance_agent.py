"""
Relevance Agent.

Filters job listings to ensure they match Yash Pal's profile.
Checks:
  - Role title matches target roles (fuzzy match)
  - Role title does NOT match excluded keywords (senior, lead, etc.)
  - Location is acceptable
  - Experience requirement is within range (0-3 years)
"""

import re
from typing import Any

from agents.base_agent import BaseAgent
from config.profile import PROFILE, TargetProfile
from scrapers.base_scraper import JobListing


class RelevanceAgent(BaseAgent):
    """Filters jobs using rule-based metrics matching Yash's target profile."""

    @property
    def name(self) -> str:
        return "relevance"

    def __init__(self, profile: TargetProfile = PROFILE) -> None:
        super().__init__()
        self._profile = profile

    def _matches_title(self, title: str) -> bool:
        """Check if the title matches target roles and has no excluded words."""
        title_lower = title.lower()

        # 1. Check exclusions
        for word in self._profile.excluded_title_keywords:
            if word in title_lower:
                # Specific check to allow e.g. "Senior NLP" if we wanted to,
                # but we reject senior/lead/manager/etc. by default.
                self.logger.debug(f"Rejecting title '{title}' due to exclusion: '{word}'")
                return False

        # 2. Check target roles
        for role in self._profile.target_roles:
            if role in title_lower:
                return True

        # Fuzzy match - check if it has 'ai', 'ml', 'fresher', 'machine learning', etc.
        # to prevent missing new variations
        fuzzy_keywords = ["ai", "ml", "nlp", "flutter", "android", "machine learning", "deep learning", "cv"]
        words = re.split(r"\W+", title_lower)
        for kw in fuzzy_keywords:
            if kw in words:
                return True

        self.logger.debug(f"Rejecting title '{title}' - no matching role keyword found.")
        return False

    def _matches_location(self, location: str) -> bool:
        """Check if location is preferred or blank (allow blank for safety)."""
        if not location:
            return True
            
        location_lower = location.lower()
        for loc in self._profile.preferred_locations:
            if loc in location_lower:
                return True

        self.logger.debug(f"Rejecting location '{location}' - not in preferred locations.")
        return False

    def _extract_experience(self, text: str) -> int | None:
        """
        Extract required years of experience from description using regex.
        Returns the maximum experience number found in patterns like '3-5 years', '2+ years'.
        """
        if not text:
            return None

        # Look for patterns like '3+ years', '2-5 years', '5 years of experience'
        # Group 1 will capture the number
        patterns = [
            r"(\d+)\+?\s*(?:years?|yrs?)\s*(?:of\s*)?experience",
            r"(?:experience\s*of\s*)?(\d+)\+?\s*(?:years?|yrs?)",
            r"(\d+)\s*-\s*\d+\s*(?:years?|yrs?)",
        ]

        max_years = 0
        found = False

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for m in matches:
                try:
                    years = int(m)
                    if years > max_years:
                        max_years = years
                        found = True
                except ValueError:
                    continue

        return max_years if found else None

    def run(self, listings: list[JobListing]) -> list[JobListing]:
        """
        Filter job listings by title, location, and experience.

        Args:
            listings: List of deduplicated JobListing objects.

        Returns:
            Filtered list of relevant JobListing objects.
        """
        relevant_listings: list[JobListing] = []

        for listing in listings:
            # 1. Filter by title
            if not self._matches_title(listing.title):
                continue

            # 2. Filter by location
            if not self._matches_location(listing.location):
                continue

            # 3. Filter by experience extracted from description
            exp_years = self._extract_experience(listing.description)
            if exp_years is not None and exp_years > self._profile.max_experience_years:
                self.logger.debug(
                    f"Rejecting {listing.company} — {listing.title} "
                    f"due to extracted exp ({exp_years} yrs > {self._profile.max_experience_years} max)"
                )
                continue

            relevant_listings.append(listing)

        self.logger.info(
            f"Relevance filtering finished: {len(listings)} input -> "
            f"{len(relevant_listings)} relevant (filtered {len(listings) - len(relevant_listings)} irrelevant)"
        )
        return relevant_listings
