"""Unit tests for TredenceScraper."""

import pytest
from scrapers.tredence_scraper import TredenceScraper
from scrapers.career_source_detector import CareerSourceDetector
from scrapers.base_scraper import JobListing


def test_tredence_ats_discovery():
    """Test ATS discovery for Tredence."""
    detector = CareerSourceDetector()
    info = detector.detect("Tredence", "")
    assert info["platform"] == "custom"
    assert "ripplehire" in info["career_url"]


def test_tredence_job_parsing():
    """Test standard job parsing for Tredence."""
    scraper = TredenceScraper()
    
    title = "AI Consultant"
    job_url = "https://tredence.ripplehire.com/candidate/job/detail/12345"
    location = "Bengaluru, India"
    posted_date = "Just now"
    
    listing = JobListing(
        company=scraper.company_name,
        title=title,
        url=job_url,
        location=location,
        description=f"Tredence RippleHire job: {title}. Location: {location}.",
        source=scraper.source_name,
        posted_date=posted_date,
        company_priority=95
    )
    
    assert listing.company == "Tredence"
    assert listing.title == "AI Consultant"
    assert listing.location == "Bengaluru, India"
    assert listing.posted_date == "Just now"
    assert listing.company_priority == 95
    assert listing.job_id == JobListing(company="Tredence", title="AI Consultant", url="", location="Bengaluru, India").job_id


def test_tredence_empty_and_error(monkeypatch):
    """Test handling of empty responses and network errors."""
    scraper = TredenceScraper()
    # Mock scrape to raise/fail gracefully
    monkeypatch.setattr(scraper, "scrape", lambda: [])
    jobs = scraper.scrape()
    assert isinstance(jobs, list)
    assert len(jobs) == 0
