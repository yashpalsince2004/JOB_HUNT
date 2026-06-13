"""Unit tests for Course5Scraper."""

import pytest
from scrapers.course5_scraper import Course5Scraper
from scrapers.career_source_detector import CareerSourceDetector
from scrapers.base_scraper import JobListing


def test_course5_ats_discovery():
    """Test that ATS discovery returns custom for Course5."""
    detector = CareerSourceDetector()
    info = detector.detect("Course5 Intelligence", "https://careers.c5i.ai/")
    assert info["platform"] == "custom"


def test_course5_job_parsing(monkeypatch):
    """Test Course5 scraper job listings creation."""
    import scrapers.course5_scraper
    monkeypatch.setattr(
        scrapers.course5_scraper,
        "sync_playwright",
        lambda: (_ for _ in ()).throw(RuntimeError("Network disabled for test"))
    )

    scraper = Course5Scraper()
    jobs = scraper.scrape()
    
    assert isinstance(jobs, list)
    assert len(jobs) > 0
    
    # Verify fallback lists
    job = jobs[0]
    assert job.company == "Course5 Intelligence"
    assert "Data Scientist" in job.title or "ML Engineer" in job.title
    assert job.source == "course5"
    assert job.company_priority == 95
    assert job.job_id is not None
