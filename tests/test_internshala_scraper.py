"""Unit tests for InternshalaScraper."""

import pytest
from bs4 import BeautifulSoup
from scrapers.internshala_scraper import InternshalaScraper
from scrapers.base_scraper import JobListing


def test_internshala_salary_normalization():
    scraper = InternshalaScraper()
    
    # Monthly stipend
    min_val, max_val, curr, period = scraper._normalize_salary("15,000 /month")
    assert min_val == 15000.0
    assert max_val == 15000.0
    assert curr == "INR"
    assert period == "monthly"

    # Annual LPA
    min_val, max_val, curr, period = scraper._normalize_salary("3 - 6 LPA")
    assert min_val == 300000.0
    assert max_val == 600000.0
    assert curr == "INR"
    assert period == "yearly"


def test_internshala_filtering():
    scraper = InternshalaScraper()
    
    # Unpaid check
    ignore, reason = scraper._should_ignore("AI Engineer", "Unpaid")
    assert ignore
    assert reason == "unpaid"
    
    # Unpaid alternate wording
    ignore, reason = scraper._should_ignore("ML Intern", "No stipend")
    assert ignore
    assert reason == "unpaid"
    
    # Marketing keyword
    ignore, reason = scraper._should_ignore("Social Media Marketing Intern", "10000/month")
    assert ignore
    assert "marketing" in reason

    # Sales keyword
    ignore, reason = scraper._should_ignore("Business Development Executive (Sales)", "15000/month")
    assert ignore
    assert "sales" in reason
    
    # Allowed role
    ignore, reason = scraper._should_ignore("Flutter Developer Intern", "10000/month")
    assert not ignore


def test_internshala_job_parsing():
    scraper = InternshalaScraper()
    
    sample_html = """
    <div class="individual_internship">
        <div class="heading_4_5 a"><a href="/job/detail/flutter-developer-intern-credible">Flutter Developer Intern</a></div>
        <a class="company_name">Credible</a>
        <div class="location_link">Work From Home</div>
        <div class="stipend">12,000 /month</div>
        <div class="status-container">2 days ago</div>
    </div>
    """
    
    soup = BeautifulSoup(sample_html, "lxml")
    card = soup.select_one(".individual_internship")
    
    title = card.select_one(".heading_4_5 a").get_text(strip=True)
    company = card.select_one(".company_name").get_text(strip=True)
    location = card.select_one(".location_link").get_text(strip=True)
    stipend = card.select_one(".stipend").get_text(strip=True)
    sal_min, sal_max, sal_curr, sal_per = scraper._normalize_salary(stipend)
    
    listing = JobListing(
        company=company,
        title=title,
        url="https://internshala.com/job/detail/flutter-developer-intern-credible",
        location=location,
        description="Flutter dev internship",
        source=scraper.source_name,
        posted_date=card.select_one(".status-container").get_text(strip=True),
        experience="0-1 years",
        salary=stipend,
        skills="Flutter, Dart",
        remote_status="remote",
        salary_min=sal_min,
        salary_max=sal_max,
        salary_currency=sal_curr,
        salary_period=sal_per,
    )
    
    assert listing.company == "Credible"
    assert listing.title == "Flutter Developer Intern"
    assert listing.location == "Work From Home"
    assert listing.remote_status == "remote"
    assert listing.salary_min == 12000.0
    assert listing.salary_max == 12000.0
    assert listing.job_id == JobListing(company="Credible", title="Flutter Developer Intern", url="", location="Work From Home").job_id
