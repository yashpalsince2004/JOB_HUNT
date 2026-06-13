"""Unit tests for ExlScraper."""

import pytest
from scrapers.exl_scraper import ExlScraper
from scrapers.career_source_detector import CareerSourceDetector
from scrapers.base_scraper import JobListing


def test_exl_ats_discovery():
    """Test that ATS discovery returns custom for EXL."""
    detector = CareerSourceDetector()
    info = detector.detect("EXL", "https://www.exlservice.com/careers")
    assert info["platform"] == "custom"


def test_exl_job_parsing(monkeypatch):
    """Test EXL scraper job listings creation."""
    import scrapers.exl_scraper
    monkeypatch.setattr(
        scrapers.exl_scraper,
        "sync_playwright",
        lambda: (_ for _ in ()).throw(RuntimeError("Network disabled for test"))
    )

    scraper = ExlScraper()
    jobs = scraper.scrape()
    
    assert isinstance(jobs, list)
    assert len(jobs) > 0
    
    # Verify fallback lists
    job = jobs[0]
    assert job.company == "EXL"
    assert "Analytics Consultant" in job.title or "Data Scientist" in job.title
    assert job.source == "exl"
    assert job.company_priority == 90
    assert job.job_id is not None
