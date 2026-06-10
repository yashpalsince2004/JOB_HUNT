"""
Resume Tailoring Agent.

Loads the master resume JSON and uses Gemini to tailor it for a specific job listing.
Outputs a tailored resume JSON structure that can be rendered to HTML/PDF.
"""

import json
from pathlib import Path
from typing import Any

from agents.base_agent import BaseAgent
from config.settings import Settings
from utils.llm_client import LLMClient


class ResumeAgent(BaseAgent):
    """Tailors the master resume for specific job descriptions using LLM instructions."""

    @property
    def name(self) -> str:
        return "resume"

    def __init__(self, llm_client: LLMClient, master_resume_path: Path | str | None = None) -> None:
        super().__init__()
        self._llm_client = llm_client
        settings = Settings()
        self._resume_path = Path(master_resume_path or settings.knowledge_dir / "master_resume.json")

    def _load_master_resume(self) -> dict[str, Any]:
        """Load master resume JSON."""
        if not self._resume_path.exists():
            raise FileNotFoundError(f"Master resume not found at {self._resume_path}")
        with open(self._resume_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def run(self, job_data: dict[str, Any]) -> dict[str, Any]:
        """
        Generate a tailored resume JSON for a specific job listing.

        Args:
            job_data: A job dictionary containing 'company', 'title', 'location', 'description', and 'analysis'.

        Returns:
            A dictionary containing the tailored resume data.
        """
        master_resume = self._load_master_resume()
        company = job_data.get("company", "Unknown Company")
        title = job_data.get("title", "Unknown Role")
        jd_analysis = job_data.get("analysis", {})

        self.logger.info(f"Tailoring resume for {title} at {company}...")

        system_prompt = (
            "You are a professional resume writer and career coach specializing in ATS optimization. "
            "Your task is to tailor a candidate's master resume JSON for a specific job description. "
            "CRITICAL: Keep all information truthful. Highlight existing relevant skills and projects, "
            "rephrase bullet points to align with the JD, and reorder skill categories. Do NOT fabricate experience."
        )

        prompt = f"""
Tailor this master resume JSON for the role "{title}" at "{company}".

Job Summary:
{jd_analysis.get('summary', '')}

Required Skills:
{', '.join(jd_analysis.get('required_skills', []))}

Responsibilities:
{', '.join(jd_analysis.get('responsibilities', []))}

Master Resume JSON:
{json.dumps(master_resume, indent=2)}

Guidelines:
1. Re-write the 'summary' to directly connect the candidate's skills with the job requirements in 2-3 sentences.
2. Select the top 2-3 most relevant 'projects' from the master resume. Reorder/optimize bullet points to emphasize relevant tech stack/outcomes matching the JD.
3. Optimize 'experience' bullet points to focus on achievements related to the JD responsibilities.
4. Reorder the 'skills' object categories and items so the skills mentioned in the JD appear first.
5. Keep the overall output size suitable for a 1-page resume.
6. Retain all personal info, education, certifications, and achievements intact.

Output MUST follow the exact same JSON structure as the input Master Resume.
"""

        try:
            tailored_resume = self._llm_client.generate_json(prompt, system_prompt)
            # Basic validation: ensure personal info is present
            if "personal_info" not in tailored_resume:
                tailored_resume["personal_info"] = master_resume.get("personal_info", {})
            return tailored_resume
        except Exception as e:
            self.logger.error(f"Failed to tailor resume: {e}")
            return master_resume
