"""
Skill Gap Analysis Agent.

Aggregates required skills across all analyzed job listings, compares them
with Yash Pal's master resume skills, and identifies high-demand gaps.
"""

import json
from collections import Counter
from pathlib import Path
from typing import Any

from agents.base_agent import BaseAgent
from config.settings import Settings
from sheets.client import SheetsClient


class SkillGapAgent(BaseAgent):
    """Analyzes and reports skill gaps between job market demand and candidate resume."""

    @property
    def name(self) -> str:
        return "skill_gap"

    def __init__(self, sheets_client: SheetsClient | None = None, master_resume_path: Path | str | None = None) -> None:
        super().__init__()
        self._sheets_client = sheets_client
        settings = Settings()
        self._resume_path = Path(master_resume_path or settings.knowledge_dir / "master_resume.json")

    def _load_resume_skills(self) -> set[str]:
        """Load skills from master resume."""
        if not self._resume_path.exists():
            return set()
        
        try:
            with open(self._resume_path, "r", encoding="utf-8") as f:
                resume = json.load(f)
            
            skills = set()
            skills_data = resume.get("skills", {})
            if isinstance(skills_data, dict):
                for category, items in skills_data.items():
                    if isinstance(items, list):
                        skills.update(str(item).lower().strip() for item in items)
            elif isinstance(skills_data, list):
                skills.update(str(item).lower().strip() for item in skills_data)
            return skills
        except Exception as e:
            self.logger.error(f"Error loading resume skills for gap analysis: {e}")
            return set()

    def run(self, analyzed_jobs: list[dict[str, Any]]) -> dict[str, int]:
        """
        Run skill gap analysis.

        Args:
            analyzed_jobs: List of job listings containing structured JD analysis.

        Returns:
            Dictionary of all aggregated skills and their demand frequencies.
        """
        self.logger.info("Running skill gap analysis...")

        # 1. Aggregate required skills from all analyzed JDs
        all_required_skills = []
        for job in analyzed_jobs:
            analysis = job.get("analysis", {})
            required = analysis.get("required_skills", [])
            for skill in required:
                all_required_skills.append(skill.strip().title())

        skill_counts = dict(Counter(all_required_skills))

        # 2. Get resume skills
        resume_skills = self._load_resume_skills()

        # 3. Identify and print top gaps
        gaps = []
        for skill, count in sorted(skill_counts.items(), key=lambda x: -x[1]):
            if skill.lower() not in resume_skills:
                gaps.append(f"{skill} (demanded in {count} jobs)")

        if gaps:
            self.logger.info(f"Top Demanded Skills NOT in your resume: {', '.join(gaps[:10])}")
        else:
            self.logger.info("No major skill gaps identified! Resume covers all demanded skills.")

        # 4. Save to Sheets if configured
        if self._sheets_client:
            try:
                self._sheets_client.update_skill_gaps(skill_counts, resume_skills)
                self.logger.info("Successfully updated Skill Gaps worksheet in Google Sheets.")
            except Exception as e:
                self.logger.error(f"Failed to save skill gaps to Google Sheets: {e}")

        return skill_counts
