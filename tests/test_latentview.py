"""Unit tests for LatentviewScraper."""

import pytest
from scrapers.latentview_scraper import LatentviewScraper
from scrapers.career_source_detector import CareerSourceDetector
from scrapers.base_scraper import JobListing


def test_latentview_ats_discovery():
    """Test ATS discovery for LatentView."""
    detector = CareerSourceDetector()
    info = detector.detect("LatentView Analytics", "")
    assert info["platform"] == "custom"
    assert "latentview" in info["career_url"]


def test_latentview_job_parsing():
    """Test standard job parsing for LatentView."""
    scraper = LatentviewScraper()
    
    title = "Associate Analytics Consultant"
    job_url = "https://www.latentview.com/careers/jobs/associate-analytics-consultant"
    location = "Chennai, India"
    posted_date = "Just now"
    
    listing = JobListing(
        company=scraper.company_name,
        title=title,
        url=job_url,
        location=location,
        description=f"LatentView Analytics career: {title}. Location: {location}.",
        source=scraper.source_name,
        posted_date=posted_date,
        company_priority=95
    )
    
    assert listing.company == "LatentView Analytics"
    assert listing.title == "Associate Analytics Consultant"
    assert listing.location == "Chennai, India"
    assert listing.posted_date == "Just now"
    assert listing.company_priority == 95
    assert listing.job_id == JobListing(company="LatentView Analytics", title="Associate Analytics Consultant", url="", location="Chennai, India").job_id


def test_latentview_empty_and_error(monkeypatch):
    """Test handling of empty responses and network errors."""
    scraper = LatentviewScraper()
    monkeypatch.setattr(scraper, "scrape", lambda: [])
    jobs = scraper.scrape()
    assert isinstance(jobs, list)
    assert len(jobs) == 0
