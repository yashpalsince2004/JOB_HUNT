"""Scraper package for AI Job Hunter Agent."""

from scrapers.base_scraper import BaseScraper, JobListing
from scrapers.greenhouse_scraper import GreenhouseScraper
from scrapers.lever_scraper import LeverScraper
from scrapers.ashby_scraper import AshbyScraper
from scrapers.smartrecruiters_scraper import SmartRecruitersScraper
from scrapers.indeed_scraper import IndeedScraper
from scrapers.wellfound_scraper import WellfoundScraper
from scrapers.workday_scraper import WorkdayScraper

__all__ = [
    "BaseScraper",
    "JobListing",
    "GreenhouseScraper",
    "LeverScraper",
    "AshbyScraper",
    "SmartRecruitersScraper",
    "IndeedScraper",
    "WellfoundScraper",
    "WorkdayScraper",
]
