"""Unit tests for NaukriScraper."""

import pytest
from bs4 import BeautifulSoup
from scrapers.naukri_scraper import NaukriScraper
from scrapers.base_scraper import JobListing


def test_naukri_salary_normalization():
    scraper = NaukriScraper()
    
    # Range LPA
    min_val, max_val, curr, period = scraper._normalize_salary("3-6 Lakhs PA")
    assert min_val == 300000.0
    assert max_val == 600000.0
    assert curr == "INR"
    assert period == "yearly"

    # Single value LPA
    min_val, max_val, curr, period = scraper._normalize_salary("10 LPA")
    assert min_val == 1000000.0
    assert max_val == 1000000.0

    # Not disclosed
    min_val, max_val, curr, period = scraper._normalize_salary("Not Disclosed")
    assert min_val == 0.0
    assert max_val == 0.0


def test_naukri_experience_extraction():
    scraper = NaukriScraper()
    
    assert scraper._extract_experience_years("0-2 Yrs") == 0
    assert scraper._extract_experience_years("3-5 Yrs") == 3
    assert scraper._extract_experience_years("Fresher") == 0
    assert scraper._extract_experience_years("") is None


def test_naukri_job_parsing():
    scraper = NaukriScraper()
    
    sample_html = """
    <div class="srp-jobtuple-wrapper">
        <a class="title" href="/job-listings-ai-engineer-fresher-google-mumbai-0-to-2-years">AI Engineer Fresher</a>
        <a class="comp-name">Google</a>
        <div class="loc-wrap"><span class="locWdth">Mumbai</span></div>
        <div class="exp-wrap"><span class="expwdth">0-2 Yrs</span></div>
        <div class="sal-wrap"><span class="sal">5-10 LPA</span></div>
        <div class="tags-gt">
            <span class="tag-li">Python</span>
            <span class="tag-li">LLM</span>
        </div>
        <div class="job-desc">Work on Generative AI systems.</div>
        <span class="posted-date">30+ days ago</span>
    </div>
    """
    
    # We can inject sample html parsing by simulating BeautifulSoup parsing in test
    soup = BeautifulSoup(sample_html, "lxml")
    card = soup.select_one(".srp-jobtuple-wrapper")
    
    # Mock how the scraper parses a single card
    title_elem = card.select_one("a.title")
    title = title_elem.get_text(strip=True)
    job_url = "https://www.naukri.com" + title_elem.get("href")
    company = card.select_one("a.comp-name").get_text(strip=True)
    location = card.select_one(".loc-wrap span.locWdth").get_text(strip=True)
    experience = card.select_one(".exp-wrap span.expwdth").get_text(strip=True)
    salary = card.select_one(".sal-wrap span.sal").get_text(strip=True)
    sal_min, sal_max, sal_curr, sal_per = scraper._normalize_salary(salary)
    
    skills = [s.get_text(strip=True) for s in card.select(".tags-gt .tag-li")]
    skills_str = ", ".join(skills)
    description = card.select_one(".job-desc").get_text(strip=True)
    posted_date = card.select_one(".posted-date").get_text(strip=True)
    
    listing = JobListing(
        company=company,
        title=title,
        url=job_url,
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
    
    assert listing.company == "Google"
    assert listing.title == "AI Engineer Fresher"
    assert listing.location == "Mumbai"
    assert listing.experience == "0-2 Yrs"
    assert listing.salary_min == 500000.0
    assert listing.salary_max == 1000000.0
    assert "Python" in listing.skills
    assert "LLM" in listing.skills
    # Check deduplication key compatibility
    assert listing.job_id == JobListing(company="Google", title="AI Engineer Fresher", url="", location="Mumbai").job_id
