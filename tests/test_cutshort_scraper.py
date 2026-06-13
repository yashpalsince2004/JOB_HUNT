"""Unit tests for CutshortScraper."""

import pytest
from bs4 import BeautifulSoup
from scrapers.cutshort_scraper import CutshortScraper
from scrapers.base_scraper import JobListing


def test_cutshort_salary_normalization():
    scraper = CutshortScraper()
    
    # LPA format
    min_val, max_val, curr, period = scraper._normalize_salary("8 - 12 LPA")
    assert min_val == 800000.0
    assert max_val == 1200000.0
    assert curr == "INR"
    
    # USD K format
    min_val, max_val, curr, period = scraper._normalize_salary("$20k - $40k")
    assert min_val == 20000.0
    assert max_val == 40000.0
    assert curr == "USD"


def test_cutshort_experience_extraction():
    scraper = CutshortScraper()
    
    assert scraper._extract_experience_years("1-3 yrs") == 1
    assert scraper._extract_experience_years("Fresher") == 0


def test_cutshort_job_parsing():
    scraper = CutshortScraper()
    
    sample_html = """
    <div class="job-card">
        <h3>Machine Learning Engineer</h3>
        <a class="company-name" href="/company/mitra-ai">MITRA AI</a>
        <div class="location">Remote, India</div>
        <div class="experience">1-3 yrs</div>
        <div class="salary">8 - 15 LPA</div>
        <div class="skill-tag">PyTorch</div>
        <div class="skill-tag">NLP</div>
        <div class="job-description">Working on LLM architectures.</div>
        <div class="posted-date">2 days ago</div>
    </div>
    """
    
    soup = BeautifulSoup(sample_html, "lxml")
    card = soup.select_one(".job-card")
    
    title = card.select_one("h3").get_text(strip=True)
    company = card.select_one(".company-name").get_text(strip=True)
    location = card.select_one(".location").get_text(strip=True)
    experience = card.select_one(".experience").get_text(strip=True)
    salary = card.select_one(".salary").get_text(strip=True)
    sal_min, sal_max, sal_curr, sal_per = scraper._normalize_salary(salary)
    
    skills = [s.get_text(strip=True) for s in card.select(".skill-tag")]
    skills_str = ", ".join(skills)
    description = card.select_one(".job-description").get_text(strip=True)
    posted_date = card.select_one(".posted-date").get_text(strip=True)
    
    listing = JobListing(
        company=company,
        title=title,
        url="https://cutshort.io/job/ml-engineer-mitra-ai",
        location=location,
        description=description,
        source=scraper.source_name,
        posted_date=posted_date,
        experience=experience,
        salary=salary,
        skills=skills_str,
        remote_status="remote",
        salary_min=sal_min,
        salary_max=sal_max,
        salary_currency=sal_curr,
        salary_period=sal_per,
    )
    
    assert listing.company == "MITRA AI"
    assert listing.title == "Machine Learning Engineer"
    assert listing.location == "Remote, India"
    assert listing.remote_status == "remote"
    assert listing.salary_min == 800000.0
    assert listing.salary_max == 1500000.0
    assert "PyTorch" in listing.skills
    assert listing.job_id == JobListing(company="MITRA AI", title="Machine Learning Engineer", url="", location="Remote, India").job_id
