"""Unit tests for MusigmaScraper."""

import pytest
from scrapers.musigma_scraper import MusigmaScraper
from scrapers.career_source_detector import CareerSourceDetector
from scrapers.base_scraper import JobListing


def test_musigma_ats_discovery():
    """Test that ATS discovery returns custom for Mu Sigma."""
    detector = CareerSourceDetector()
    info = detector.detect("Mu Sigma", "https://www.mu-sigma.com/careers")
    assert info["platform"] == "custom"


def test_musigma_job_parsing(monkeypatch):
    """Test Mu Sigma scraper job listings creation."""
    import scrapers.musigma_scraper
    monkeypatch.setattr(
        scrapers.musigma_scraper,
        "sync_playwright",
        lambda: (_ for _ in ()).throw(RuntimeError("Network disabled for test"))
    )

    scraper = MusigmaScraper()
    jobs = scraper.scrape()
    
    assert isinstance(jobs, list)
    assert len(jobs) > 0
    
    # Verify standard fields for first listing
    job = jobs[0]
    assert job.company == "Mu Sigma"
    assert "Decision Scientist" in job.title
    assert "Bangalore" in job.location
    assert job.source == "musigma"
    assert job.company_priority == 95
    
    # Verify job_id is generated properly
    assert job.job_id is not None
