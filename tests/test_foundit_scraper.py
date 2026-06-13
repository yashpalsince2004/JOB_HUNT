"""Unit tests for FounditScraper."""

import pytest
from bs4 import BeautifulSoup
from scrapers.foundit_scraper import FounditScraper
from scrapers.base_scraper import JobListing


def test_foundit_salary_normalization():
    scraper = FounditScraper()
    
    # LPA format
    min_val, max_val, curr, period = scraper._normalize_salary("5 - 8 LPA")
    assert min_val == 500000.0
    assert max_val == 800000.0
    assert curr == "INR"


def test_foundit_experience_extraction():
    scraper = FounditScraper()
    
    assert scraper._extract_experience_years("0-3 Years") == 0
    assert scraper._extract_experience_years("Fresher") == 0


def test_foundit_job_parsing():
    scraper = FounditScraper()
    
    sample_html = """
    <div class="card-container">
        <h3 class="job-title"><a href="/job/python-developer-accenture">Python Developer</a></h3>
        <span class="company">Accenture</span>
        <span class="location">Pune, India</span>
        <span class="exp">0-3 Years</span>
        <span class="salary">6 - 9 LPA</span>
        <span class="skill-tag">Python</span>
        <span class="skill-tag">Flask</span>
        <div class="job-description">Design REST APIs.</div>
        <span class="posted">Just now</span>
    </div>
    """
    
    soup = BeautifulSoup(sample_html, "lxml")
    card = soup.select_one(".card-container")
    
    title = card.select_one(".job-title").get_text(strip=True)
    company = card.select_one(".company").get_text(strip=True)
    location = card.select_one(".location").get_text(strip=True)
    experience = card.select_one(".exp").get_text(strip=True)
    salary = card.select_one(".salary").get_text(strip=True)
    sal_min, sal_max, sal_curr, sal_per = scraper._normalize_salary(salary)
    
    skills = [s.get_text(strip=True) for s in card.select(".skill-tag")]
    skills_str = ", ".join(skills)
    description = card.select_one(".job-description").get_text(strip=True)
    posted_date = card.select_one(".posted").get_text(strip=True)
    
    listing = JobListing(
        company=company,
        title=title,
        url="https://www.foundit.in/job/python-developer-accenture",
        location=location,
        description=description,
        source=scraper.source_name,
        posted_date=posted_date,
        experience=experience,
        salary=salary,
        skills=skills_str,
        remote_status="onsite",
        salary_min=sal_min,
        salary_max=sal_max,
        salary_currency=sal_curr,
        salary_period=sal_per,
    )
    
    assert listing.company == "Accenture"
    assert listing.title == "Python Developer"
    assert listing.location == "Pune, India"
    assert listing.salary_min == 600000.0
    assert listing.salary_max == 900000.0
    assert "Python" in listing.skills
    assert listing.job_id == JobListing(company="Accenture", title="Python Developer", url="", location="Pune, India").job_id
