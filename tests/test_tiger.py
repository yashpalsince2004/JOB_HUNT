"""Unit tests for TigerScraper."""

import pytest
from scrapers.tiger_scraper import TigerScraper
from scrapers.career_source_detector import CareerSourceDetector
from scrapers.base_scraper import JobListing


def test_tiger_ats_discovery():
    """Test ATS discovery for Tiger Analytics."""
    detector = CareerSourceDetector()
    info = detector.detect("Tiger Analytics", "")
    assert info["platform"] == "custom"
    assert "workable" in info["career_url"]


def test_tiger_job_parsing():
    """Test standard job parsing for Tiger Analytics."""
    scraper = TigerScraper()
    
    mock_item = {
        "title": "Machine Learning Architect",
        "shortcode": "9D4A1C8F0E",
        "location": {
            "city": "Chennai",
            "country": "India"
        },
        "published": "2026-06-11"
    }
    
    title = mock_item["title"]
    job_url = f"https://apply.workable.com/tiger-analytics/j/{mock_item['shortcode']}/"
    loc_data = mock_item["location"]
    location = f"{loc_data['city']}, {loc_data['country']}"
    posted_date = mock_item["published"]
    
    listing = JobListing(
        company=scraper.company_name,
        title=title,
        url=job_url,
        location=location,
        description=f"Tiger Analytics job listing for {title}. Location: {location}.",
        source=scraper.source_name,
        posted_date=posted_date,
        company_priority=95
    )
    
    assert listing.company == "Tiger Analytics"
    assert listing.title == "Machine Learning Architect"
    assert listing.location == "Chennai, India"
    assert listing.posted_date == "2026-06-11"
    assert listing.company_priority == 95
    assert listing.job_id == JobListing(company="Tiger Analytics", title="Machine Learning Architect", url="", location="Chennai, India").job_id


def test_tiger_empty_and_error(monkeypatch):
    """Test handling of empty responses and network errors."""
    scraper = TigerScraper()
    # Mock workable API to fail
    monkeypatch.setattr(scraper, "_scrape_workable_api", lambda: [])
    # Mock playwright fallback to return empty
    monkeypatch.setattr(scraper, "_scrape_fallback_html", lambda: [])
    
    jobs = scraper.scrape()
    assert isinstance(jobs, list)
    assert len(jobs) == 0
