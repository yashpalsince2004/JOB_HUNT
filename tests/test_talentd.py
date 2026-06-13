"""Unit tests for TalentdScraper."""

import pytest
from scrapers.talentd_scraper import TalentdScraper
from scrapers.base_scraper import JobListing


def test_talentd_salary_normalization():
    """Test salary parsing for Talentd."""
    scraper = TalentdScraper()
    
    # LPA format
    val_min, val_max, curr, period = scraper._normalize_salary("6 LPA")
    assert val_min == 600000.0
    assert val_max == 600000.0
    assert curr == "INR"
    assert period == "yearly"

    # Monthly format
    val_min, val_max, curr, period = scraper._normalize_salary("25,000 / pm")
    assert val_min == 25000.0
    assert val_max == 25000.0
    assert curr == "INR"
    assert period == "monthly"

    # Not disclosed
    val_min, val_max, curr, period = scraper._normalize_salary("Not Disclosed")
    assert val_min == 0.0
    assert val_max == 0.0


def test_talentd_job_parsing(monkeypatch):
    """Test Talentd scraper job listings creation."""
    import scrapers.talentd_scraper
    monkeypatch.setattr(
        scrapers.talentd_scraper,
        "sync_playwright",
        lambda: (_ for _ in ()).throw(RuntimeError("Network disabled for test"))
    )

    scraper = TalentdScraper()
    jobs = scraper.scrape()
    
    assert isinstance(jobs, list)
    assert len(jobs) > 0
    
    # Verify fallback lists
    job = jobs[0]
    assert job.source == "talentd"
    assert job.job_id is not None
