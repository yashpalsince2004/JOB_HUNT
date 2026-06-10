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
    assert agent._extract_experience("Experience: 2-4 years.") == 4
    assert agent._extract_experience("No experience required. Freshers welcome!") is None
    assert agent._extract_experience("Looking for 1 year of experience.") == 1


def test_dedup_agent_normalization():
    """Test that URLs are normalized properly for deduplication."""
    agent = DedupAgent()

    url1 = "https://boards.greenhouse.io/stripe/jobs/123?gh_jid=123&utm_source=indeed"
    url2 = "https://boards.greenhouse.io/stripe/jobs/123"
    
    assert agent._normalize_url(url1) == agent._normalize_url(url2)
