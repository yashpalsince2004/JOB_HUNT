"""Unit tests for pipeline agents."""

import pytest
from agents.dedup_agent import DedupAgent
from agents.relevance_agent import RelevanceAgent
from scrapers.base_scraper import JobListing


def test_relevance_agent_title_matching():
    """Test that the relevance agent correctly identifies matching roles."""
    agent = RelevanceAgent()

    # Matches
    assert agent._matches_title("AI Engineer")
    assert agent._matches_title("Junior ML Engineer")
    assert agent._matches_title("Flutter Developer fresher")
    assert agent._matches_title("Generative AI Developer")

    # Exclusions
    assert not agent._matches_title("Senior AI Engineer")
    assert not agent._matches_title("Lead Flutter Developer")
    assert not agent._matches_title("HR Manager")


def test_relevance_agent_location_matching():
    """Test location filters."""
    agent = RelevanceAgent()

    assert agent._matches_location("Mumbai")
    assert agent._matches_location("Pune")
    assert agent._matches_location("Remote, India")
    assert agent._matches_location("Bangalore, Karnataka")
    
    # Excluded
    assert not agent._matches_location("San Francisco, CA")
    assert not agent._matches_location("New York")


def test_relevance_agent_experience_extractor():
    """Test regex extraction of experience requirements."""
    agent = RelevanceAgent()

    assert agent._extract_experience("Requires 5+ years of experience in deep learning.") == 5
    assert agent._extract_experience("Experience: 2-4 years.") == 2
    assert agent._extract_experience("No experience required. Freshers welcome!") is None
    assert agent._extract_experience("Looking for 1 year of experience.") == 1


def test_relevance_agent_scoring():
    """Test the new relevance scoring system components."""
    agent = RelevanceAgent()

    # 1. Title Match Score
    # Exact target role match
    score, reason = agent._calculate_title_score("Applied AI Engineer")
    assert score == 40
    assert "Exact match" in reason

    # Fuzzy match with word overlap
    score, reason = agent._calculate_title_score("GenAI Solutions Engineer")
    assert score == 40
    assert "match" in reason

    # Fuzzy token overlap
    score, reason = agent._calculate_title_score("Junior Deep Learning Specialist")
    assert score == 26
    assert "Fuzzy match" in reason

    # Fuzzy keyword fallback
    score, reason = agent._calculate_title_score("CV Consultant")
    assert score == 20
    assert "fuzzy keywords" in reason

    # No match
    score, reason = agent._calculate_title_score("Accountant")
    assert score == 0
    assert "No title match" in reason

    # 2. Skill Match Score
    # 0 skills
    score, skills = agent._calculate_skill_score("Title", "No skills here")
    assert score == 0
    # 2 skills (python, pytorch)
    score, skills = agent._calculate_skill_score("Title", "We use python and pytorch for development.")
    assert score == 12
    assert "python" in skills
    assert "pytorch" in skills

    # 3. Location Match Score
    # Preferred location (Mumbai)
    is_valid, score, reason = agent._evaluate_location("Mumbai, India")
    assert is_valid
    assert score == 100

    # General Remote India
    is_valid, score, reason = agent._evaluate_location("Remote, India")
    assert is_valid
    assert score == 90

    # Secondary Indian Tech Hub (Bangalore)
    is_valid, score, reason = agent._evaluate_location("Bangalore, India")
    assert is_valid
    assert score == 75

    # Global remote
    is_valid, score, reason = agent._evaluate_location("London (Remote)")
    assert is_valid
    assert score == 85

    # On-site outside preferred locations
    is_valid, score, reason = agent._evaluate_location("San Francisco, CA")
    assert not is_valid
    assert score == 0

    # 4. Experience Match Score
    # Entry-level role overrides high exp
    is_valid, score, reason = agent._evaluate_experience("Graduate AI Engineer", "Requires 5+ years of experience.")
    assert is_valid
    assert score == 20

    # Normal within range
    is_valid, score, reason = agent._evaluate_experience("AI Engineer", "Looking for 2 years of experience.")
    assert is_valid
    assert score == 20

    # Exceeds max range
    is_valid, score, reason = agent._evaluate_experience("AI Engineer", "Requires 5 years of experience.")
    assert not is_valid
    assert score == 0


def test_dedup_agent_normalization():
    """Test that URLs are normalized properly for deduplication."""
    agent = DedupAgent()

    url1 = "https://boards.greenhouse.io/stripe/jobs/123?gh_jid=123&utm_source=indeed"
    url2 = "https://boards.greenhouse.io/stripe/jobs/123"
    
    assert agent._normalize_url(url1) == agent._normalize_url(url2)


def test_resume_compilation():
    """Test that the master resume compiles to a PDF using the generator and tectonic."""
    import json
    from pathlib import Path
    from resume.generator import ResumeGenerator

    project_root = Path(__file__).resolve().parent.parent
    master_resume_path = project_root / "knowledge" / "master_resume.json"
    assert master_resume_path.exists()

    with open(master_resume_path, "r", encoding="utf-8") as f:
        resume_data = json.load(f)

    generator = ResumeGenerator()
    output_filename = "test_test_suite_resume.pdf"

    # Generate the PDF
    pdf_path = generator.generate_pdf(resume_data, output_filename)

    assert pdf_path.exists()
    assert pdf_path.stat().st_size > 0

    # Cleanup generated files
    if pdf_path.exists():
        pdf_path.unlink()
    tex_path = pdf_path.with_suffix(".tex")
    if tex_path.exists():
        tex_path.unlink()


def test_relevance_agent_classification_and_job_scoring():
    """Test the role classifier, company priority, and weighted job scoring."""
    agent = RelevanceAgent()

    # 1. Role Classification
    c1 = agent.classify_role("Generative AI Engineer", "Working on LLM applications, RAG and fine-tuning with Python.")
    assert c1["category"] == "GENAI_ENGINEERING"
    assert c1["confidence"] >= 90

    c2 = agent.classify_role("Flutter Developer", "Build premium mobile applications with Dart.")
    assert c2["category"] == "FLUTTER"

    c3 = agent.classify_role("Accountant", "Manage corporate books and filings.")
    assert c3["category"] == "OTHER"

    # 2. Company Priority
    assert agent._get_company_priority("Google") == 100
    assert agent._get_company_priority("Quantiphi") == 100
    assert agent._get_company_priority("TCS") == 90
    assert agent._get_company_priority("Unknown Startup") == 70

    # 3. Weighted Job Scoring Formula
    # Formula: 0.30 * role_score + 0.25 * location_score + 0.20 * skill_score + 0.15 * company_score + 0.10 * freshness_score
    listing = JobListing(
        company="Google",
        title="Generative AI Engineer",
        location="Pune",
        description="We are looking for a Generative AI Engineer to build LLM products. Required skills: Python, PyTorch, LLM, Firebase.",
        url="https://google.com/jobs/1"
    )
    relevant = agent.run([listing])
    assert len(relevant) == 1
    assert relevant[0].role_category == "GENAI_ENGINEERING"
    assert relevant[0].job_score >= 80.0
    assert relevant[0].company_priority == 100


def test_ats_scoring_agent_refactor():
    """Test ATS Scoring Agent with refactored weights and project relevance."""
    from agents.ats_scoring_agent import ATSScoringAgent
    
    agent = ATSScoringAgent()
    
    # Check project relevance
    proj_score1 = agent._calculate_project_relevance("Looking for LLM and GenAI experience.")
    assert proj_score1 == 40  # Matches MITRA AI (+20) and AI Job Hunter because 'ai' is in 'genai' (+20)
    
    proj_score2 = agent._calculate_project_relevance("Python backend development using Flutter.")
    assert proj_score2 == 35  # Matches AI Job Hunter (Python/Backend: +20) and BookMyTurf (Flutter: +15)


