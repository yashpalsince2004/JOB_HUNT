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


def test_greenhouse_limit_enforcement(monkeypatch):
    """Test that GreenhouseScraper respects max_jobs_limit."""
    mock_jobs = [
        {"title": f"Job {i}", "absolute_url": f"http://example.com/job{i}", "location": {"name": "Remote"}, "content": "Desc"}
        for i in range(5)
    ]
    
    from scrapers.base_scraper import BaseScraper
    monkeypatch.setattr(BaseScraper, "_get_json", lambda self, url, params=None: {"jobs": mock_jobs})
    
    company = CompanyConfig(name="MockCompany", platform="greenhouse", board_id="mock_id")
    scraper = GreenhouseScraper(companies=[company], max_jobs_limit=3)
    
    results = scraper.scrape()
    
    assert len(results) == 3
    assert results[0].title == "Job 0"
    assert results[1].title == "Job 1"
    assert results[2].title == "Job 2"


def test_latex_escaping():
    """Test that LaTeX special characters are properly escaped."""
    from resume.generator import escape_latex_data
    
    input_data = {
        "text": "Software & AI Engineering at X_Company.",
        "skills": ["Python", "FastAPI & RAG", "Model_Fine_Tuning"],
        "nested": {
            "percentage": "99.9% accuracy",
            "nested_list": ["Hello $100", "Use #tag"]
        }
    }
    
    escaped = escape_latex_data(input_data)
    
    assert escaped["text"] == "Software \\& AI Engineering at X\\_Company."
    assert escaped["skills"][1] == "FastAPI \\& RAG"
    assert escaped["skills"][2] == "Model\\_Fine\\_Tuning"
    assert escaped["nested"]["percentage"] == "99.9\\% accuracy"
    assert escaped["nested"]["nested_list"][0] == "Hello \\$100"
    assert escaped["nested"]["nested_list"][1] == "Use \\#tag"
