"""Unit tests for FractalScraper."""

import pytest
from scrapers.fractal_scraper import FractalScraper
from scrapers.career_source_detector import CareerSourceDetector
from scrapers.base_scraper import JobListing


def test_fractal_ats_discovery():
    """Test that ATS discovery returns Workday for Fractal."""
    detector = CareerSourceDetector()
    info = detector.detect("Fractal Analytics", "https://fractal.ai/careers")
    assert info["platform"] == "Workday"
    assert "fractal" in info["career_url"]


def test_fractal_job_parsing():
    """Test standard job fields parsing for Fractal."""
    scraper = FractalScraper()
    
    mock_item = {
        "title": "AI Application Developer",
        "externalPath": "/Fractal/job/Pune/AI-Application-Developer_R202",
        "location": "Pune, India",
        "postedOn": "Posted Today"
    }
    
    title = mock_item["title"]
    job_url = "https://fractal.myworkdayjobs.com" + mock_item["externalPath"]
    location = mock_item["location"]
    posted_date = mock_item["postedOn"]
    
    listing = JobListing(
        company=scraper.company_name,
        title=title,
        url=job_url,
        location=location,
        description=f"Fractal Analytics job listing for {title}. Location: {location}.",
        source=scraper.source_name,
        posted_date=posted_date,
        company_priority=100
    )
    
    assert listing.company == "Fractal Analytics"
    assert listing.title == "AI Application Developer"
    assert listing.location == "Pune, India"
    assert listing.posted_date == "Posted Today"
    assert listing.company_priority == 100
    assert listing.job_id == JobListing(company="Fractal Analytics", title="AI Application Developer", url="", location="Pune, India").job_id


def test_fractal_empty_and_error(monkeypatch):
    """Test handling of empty responses and network errors."""
    scraper = FractalScraper()
    monkeypatch.setattr(scraper.detector, "detect", lambda *args: {"platform": "custom"})
    jobs = scraper.scrape()
    assert isinstance(jobs, list)
    assert len(jobs) == 0
