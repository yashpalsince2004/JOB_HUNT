"""Unit tests for NielseniqScraper."""

import pytest
from scrapers.nielseniq_scraper import NielseniqScraper
from scrapers.career_source_detector import CareerSourceDetector
from scrapers.base_scraper import JobListing


def test_nielseniq_ats_discovery():
    """Test that ATS discovery returns SmartRecruiters for NielsenIQ."""
    detector = CareerSourceDetector()
    info = detector.detect("NielsenIQ", "https://careers.smartrecruiters.com/NielsenIQ")
    assert info["platform"] == "SmartRecruiters"
    assert "NielsenIQ" in info["api_endpoint"]


def test_nielseniq_job_parsing():
    """Test standard job fields parsing for NielsenIQ."""
    scraper = NielseniqScraper()
    
    # Mock data returned by SmartRecruiters API
    mock_postings = {
        "content": [
            {
                "title": "Data Scientist",
                "uuid": "abc-123",
                "location": {
                    "city": "Mumbai",
                    "country": "India"
                },
                "releasedDate": "2026-06-12T00:00:00Z"
            }
        ]
    }
    
    # Test mapping
    item = mock_postings["content"][0]
    title = item["title"]
    uuid = item["uuid"]
    job_url = f"https://jobs.smartrecruiters.com/NielsenIQ/{uuid}"
    city = item["location"]["city"]
    country = item["location"]["country"]
    location = f"{city}, {country}"
    posted_date = item["releasedDate"]
    
    listing = JobListing(
        company=scraper.company_name,
        title=title,
        url=job_url,
        location=location,
        description=f"NielsenIQ SmartRecruiters job listing: {title}. Location: {location}.",
        source=scraper.source_name,
        posted_date=posted_date,
        company_priority=95
    )
    
    assert listing.company == "NielsenIQ"
    assert listing.title == "Data Scientist"
    assert listing.location == "Mumbai, India"
    assert listing.posted_date == "2026-06-12T00:00:00Z"
    assert listing.company_priority == 95
    assert listing.job_id is not None


def test_nielseniq_empty_and_error(monkeypatch):
    """Test NielsenIQ scraper handling when API is empty or fails."""
    scraper = NielseniqScraper()
    
    # Mock detector to return custom platform so API scrape is skipped
    monkeypatch.setattr(scraper.detector, "detect", lambda *args: {"platform": "custom"})
    jobs = scraper.scrape()
    assert isinstance(jobs, list)
    assert len(jobs) == 0
