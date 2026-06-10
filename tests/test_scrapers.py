"""Unit tests for job scrapers."""

import pytest
from scrapers.greenhouse_scraper import GreenhouseScraper
from config.companies import CompanyConfig


def test_greenhouse_html_cleaner():
    """Test that HTML tags are removed from descriptions correctly."""
    scraper = GreenhouseScraper(companies=[])
    
    html = "<div><h3>Role</h3><p>We are looking for a Python developer.<br>Requirements: PyTorch.</p></div>"
    cleaned = scraper._clean_html(html)
    
    assert "Role" in cleaned
    assert "We are looking for a Python developer." in cleaned
    assert "Requirements: PyTorch." in cleaned
    assert "<div>" not in cleaned
    assert "<br>" not in cleaned
