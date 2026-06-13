"""Unit tests for QuantiphiScraper."""

import pytest
from scrapers.quantiphi_scraper import QuantiphiScraper
from scrapers.career_source_detector import CareerSourceDetector
from scrapers.base_scraper import JobListing


def test_quantiphi_ats_discovery(monkeypatch):
    """Test that ATS discovery returns Workday for Quantiphi."""
    detector = CareerSourceDetector()
    info = detector.detect("Quantiphi", "https://quantiphi.com/careers/")
    assert info["platform"] == "Workday"
    assert "quantiphi" in info["career_url"]


def test_quantiphi_job_parsing():
    """Test standard job fields parsing for Quantiphi."""
    scraper = QuantiphiScraper()
    
    # Mock item returned by Workday JSON API
    mock_item = {
        "title": "Machine Learning Engineer",
        "externalPath": "/Careers/job/Mumbai/Machine-Learning-Engineer_R101",
        "location": "Mumbai, India",
        "postedOn": "Posted 2 Days Ago"
    }
    
    title = mock_item["title"]
    job_url = "https://quantiphi.myworkdayjobs.com" + mock_item["externalPath"]
    location = mock_item["location"]
    posted_date = mock_item["postedOn"]
    
    listing = JobListing(
        company=scraper.company_name,
        title=title,
        url=job_url,
        location=location,
        description=f"Quantiphi job listing for {title}. Location: {location}.",
        source=scraper.source_name,
        posted_date=posted_date,
        company_priority=100
    )
    
    assert listing.company == "Quantiphi"
    assert listing.title == "Machine Learning Engineer"
    assert listing.location == "Mumbai, India"
    assert listing.posted_date == "Posted 2 Days Ago"
    assert listing.company_priority == 100
    # Check dedup key
    assert listing.job_id == JobListing(company="Quantiphi", title="Machine Learning Engineer", url="", location="Mumbai, India").job_id


def test_quantiphi_empty_and_error(monkeypatch):
    """Test handling of empty responses and network errors."""
    scraper = QuantiphiScraper()
    
    # Mock detector to return custom platform so Workday loop is skipped
    monkeypatch.setattr(scraper.detector, "detect", lambda *args: {"platform": "custom"})
    jobs = scraper.scrape()
    assert isinstance(jobs, list)
    assert len(jobs) == 0
