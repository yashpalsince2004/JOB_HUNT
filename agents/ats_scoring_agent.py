"""
ATS Scoring Agent.

Calculates a suitability score (0-100) for a job listing against the master resume.
Uses keyword overlap (40% weight) and semantic similarity via sentence-transformers (60% weight).
Falls back gracefully to keyword overlap if sentence-transformers is not available.
"""

import json
from pathlib import Path
from typing import Any

from agents.base_agent import BaseAgent
from config.settings import Settings


class ATSScoringAgent(BaseAgent):
    """Calculates ATS matching scores for job listings against the user's master resume."""

    @property
    def name(self) -> str:
        return "ats_scoring"

    def __init__(self, master_resume_path: Path | str | None = None) -> None:
        super().__init__()
        settings = Settings()
        self._resume_path = Path(master_resume_path or settings.knowledge_dir / "master_resume.json")
        self._model = None
        self._model_initialized = False

        # Try initializing SentenceTransformer
        try:
            from sentence_transformers import SentenceTransformer
            # Use a tiny, fast model
            self.logger.info("Initializing SentenceTransformer (all-MiniLM-L6-v2)...")
            self._model = SentenceTransformer("all-MiniLM-L6-v2")
            self._model_initialized = True
            self.logger.info("SentenceTransformer initialized successfully.")
        except Exception as e:
            self.logger.warning(
                f"Failed to initialize sentence-transformers: {e}. "
                "Falling back to keyword-only scoring."
            )

    def _load_resume_text(self) -> tuple[set[str], str]:
        """Load and extract skills and text representation of the master resume."""
        if not self._resume_path.exists():
            self.logger.error(f"Master resume not found at {self._resume_path}!")
            return set(), ""

        try:
            with open(self._resume_path, "r", encoding="utf-8") as f:
                resume = json.load(f)

            # Extract skills as a set
            skills_set = set()
            skills_data = resume.get("skills", {})
            if isinstance(skills_data, dict):
                for category, items in skills_data.items():
                    if isinstance(items, list):
                        skills_set.update(str(item).lower().strip() for item in items)
            elif isinstance(skills_data, list):
                skills_set.update(str(item).lower().strip() for item in skills_data)

            # Build semantic text representation
            text_parts = []
            
            # Summary
            if resume.get("summary"):
                text_parts.append(resume["summary"])
                
            # Experience
            for exp in resume.get("experience", []):
                role_desc = f"{exp.get('role', '')} at {exp.get('company', '')}. "
                if exp.get("description"):
                    role_desc += " ".join(exp["description"])
                text_parts.append(role_desc)
                
            # Projects
            for proj in resume.get("projects", []):
                proj_desc = f"Project: {proj.get('title', '')} ({proj.get('role', '')}). "
                if proj.get("description"):
                    proj_desc += " ".join(proj["description"])
                text_parts.append(proj_desc)

            resume_text = " ".join(text_parts)
            return skills_set, resume_text

        except Exception as e:
            self.logger.error(f"Error reading master resume: {e}")
            return set(), ""

    def _calculate_cosine_similarity(self, text1: str, text2: str) -> float:
        """Calculate cosine similarity using sentence-transformers."""
        if not self._model_initialized or not self._model:
            return 0.0
        try:
            embeddings = self._model.encode([text1, text2], convert_to_tensor=True)
            # cosine similarity
            from sentence_transformers.util import cos_sim
            similarity = cos_sim(embeddings[0], embeddings[1])
            return float(similarity.item())
        except Exception as e:
            self.logger.warning(f"Error calculating semantic similarity: {e}")
            return 0.0

    def run(self, analyzed_jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """
        Score job listings and filter out those below the threshold.

        Args:
            analyzed_jobs: List of job dicts from JDAnalysisAgent.

        Returns:
            List of job dicts updated with 'ats_score' and filtered if score matches requirements.
        """
        settings = Settings()
        threshold = settings.min_ats_score
        scored_jobs = []

        resume_skills, resume_text = self._load_resume_text()
        if not resume_skills and not resume_text:
            self.logger.warning("Empty master resume. Scoring all jobs as 0.")
            for job in analyzed_jobs:
                job["ats_score"] = 0
                scored_jobs.append(job)
            return scored_jobs

        for job in analyzed_jobs:
            analysis = job.get("analysis", {})
            required_skills = [s.lower().strip() for s in analysis.get("required_skills", [])]
            ats_keywords = [k.lower().strip() for k in analysis.get("ats_keywords", [])]

            # 1. Keyword Score
            target_keywords = set(required_skills + ats_keywords)
            if not target_keywords:
                keyword_score = 50.0  # Default neutral score
            else:
                matches = 0
                for kw in target_keywords:
                    # Check if keyword is in resume skills or text
                    if kw in resume_skills or kw in resume_text.lower():
                        matches += 1
                keyword_score = (matches / len(target_keywords)) * 100.0

            # 2. Semantic Score
            jd_text = f"{analysis.get('summary', '')} " + " ".join(analysis.get("responsibilities", []))
            if self._model_initialized:
                semantic_score = self._calculate_cosine_similarity(resume_text, jd_text) * 100.0
                # Bound similarity to positive values
                semantic_score = max(0.0, semantic_score)
                # Final weighted score
                final_score = round(0.4 * keyword_score + 0.6 * semantic_score, 1)
            else:
                # Fallback to pure keyword score
                final_score = round(keyword_score, 1)

            job["ats_score"] = final_score
            self.logger.info(
                f"Scored {job.get('company')} — {job.get('title')}: "
                f"ATS Score = {final_score} (Keywords: {keyword_score:.1f}, Semantic: {semantic_score if self._model_initialized else 'N/A'})"
            )

            # Keep all jobs but tag them so we can filter later or let them proceed
            scored_jobs.append(job)

        # Sort jobs by ATS score descending
        scored_jobs.sort(key=lambda x: x.get("ats_score", 0), reverse=True)
        return scored_jobs
