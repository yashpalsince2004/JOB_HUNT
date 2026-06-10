"""
Job Description (JD) Analysis Agent.

Uses Gemini API (via LLMClient) to parse unstructured job descriptions into
structured JSON data containing keywords, skills, and requirements.
"""

from typing import Any

from agents.base_agent import BaseAgent
from scrapers.base_scraper import JobListing
from utils.llm_client import LLMClient


class JDAnalysisAgent(BaseAgent):
    """Parses and structures job descriptions using LLM analysis."""

    @property
    def name(self) -> str:
        return "jd_analysis"

    def __init__(self, llm_client: LLMClient) -> None:
        super().__init__()
        self._llm_client = llm_client

    def _analyze_jd(self, listing: JobListing) -> dict[str, Any]:
        """Send job description to LLM and return structured analysis."""
        system_prompt = (
            "You are an expert technical recruiter and ATS optimization assistant. "
            "Your task is to analyze the provided job description and extract structural details."
        )

        prompt = f"""
Analyze the following job description for the company "{listing.company}" and title "{listing.title}".
Extract the key details into the required JSON schema.

Job Description:
{listing.description}

Required JSON Output Schema:
{{
    "required_skills": ["List of core, non-negotiable technical skills required"],
    "preferred_skills": ["List of nice-to-have skills, tools, or frameworks"],
    "ats_keywords": ["Important keywords, phrases, or industry terms that an ATS would scan for"],
    "experience_level": "The expected years of experience or seniority level (e.g. '0-2 years', 'fresher')",
    "responsibilities": ["Top 3-5 core duties or responsibilities"],
    "summary": "A concise 2-sentence summary of what this role entails"
}}
"""
        try:
            analysis = self._llm_client.generate_json(prompt, system_prompt)
            return analysis
        except Exception as e:
            self.logger.error(f"Failed to analyze JD for {listing.company} - {listing.title}: {e}")
            # Fallback structure
            return {
                "required_skills": [],
                "preferred_skills": [],
                "ats_keywords": [],
                "experience_level": "Unknown",
                "responsibilities": [],
                "summary": "Failed to analyze job description."
            }

    def run(self, listings: list[JobListing]) -> list[dict[str, Any]]:
        """
        Analyze a list of job listings.

        Args:
            listings: List of relevant JobListing objects.

        Returns:
            List of dictionaries combining the original listing details with the structured analysis.
        """
        analyzed_listings: list[dict[str, Any]] = []

        for listing in listings:
            self.logger.info(f"Analyzing JD for {listing.company} — {listing.title}")
            analysis = self._analyze_jd(listing)
            
            # Merge job listing data with analysis
            job_data = listing.to_dict()
            job_data["analysis"] = analysis
            analyzed_listings.append(job_data)

        self.logger.info(f"Successfully analyzed {len(analyzed_listings)} JDs.")
        return analyzed_listings
