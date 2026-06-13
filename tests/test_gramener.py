"""Unit tests for GramenerScraper."""

import pytest
from scrapers.gramener_scraper import GramenerScraper
from scrapers.career_source_detector import CareerSourceDetector
from scrapers.base_scraper import JobListing


def test_gramener_ats_discovery():
    """Test that ATS discovery returns custom for Gramener."""
    detector = CareerSourceDetector()
    info = detector.detect("Gramener", "https://gramener.com/careers/")
    assert info["platform"] == "custom"


def test_gramener_job_parsing(monkeypatch):
    """Test Gramener scraper job listings creation."""
    import scrapers.gramener_scraper
    monkeypatch.setattr(
        scrapers.gramener_scraper,
        "sync_playwright",
        lambda: (_ for _ in ()).throw(RuntimeError("Network disabled for test"))
    )

    scraper = GramenerScraper()
    jobs = scraper.scrape()
    
    assert isinstance(jobs, list)
    assert len(jobs) > 0
    
    # Verify fallback lists
    job = jobs[0]
    assert job.company == "Gramener"
    assert "Data Scientist" in job.title or "Python Developer" in job.title
    assert job.source == "gramener"
    assert job.company_priority == 95
    assert job.job_id is not None
