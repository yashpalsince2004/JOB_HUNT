"""
Interview Preparation Agent.

Uses Gemini API to generate customized interview questions, coding problems,
system design tasks, and behavioral outlines tailored to a specific job description.
"""

from pathlib import Path
from typing import Any

from agents.base_agent import BaseAgent
from config.settings import Settings
from utils.llm_client import LLMClient


class InterviewAgent(BaseAgent):
    """Generates role-specific interview preparation resources using Gemini."""

    @property
    def name(self) -> str:
        return "interview_prep"

    def __init__(self, llm_client: LLMClient) -> None:
        super().__init__()
        self._llm_client = llm_client
        self.settings = Settings()

    def run(self, job_data: dict[str, Any]) -> Path | None:
        """
        Generate interview preparation materials for a specific job listing.

        Args:
            job_data: A job listing dictionary containing company, title, location, description, and analysis.

        Returns:
            Path to the saved interview preparation markdown file.
        """
        company = job_data.get("company", "Unknown Company")
        title = job_data.get("title", "Unknown Role")
        jd_analysis = job_data.get("analysis", {})

        self.logger.info(f"Generating interview prep material for {title} at {company}...")

        system_prompt = (
            "You are a technical interviewer at top tech firms (Google, Stripe, OpenAI). "
            "Your task is to generate a highly customized interview preparation sheet for a candidate "
            "based on a specific job description and title."
        )

        prompt = f"""
Create a comprehensive interview preparation guide for Yash Pal applying for "{title}" at "{company}".

Job Summary:
{jd_analysis.get('summary', '')}

Key Requirements & Tech Stack:
{', '.join(jd_analysis.get('required_skills', []))}

Responsibilities:
{', '.join(jd_analysis.get('responsibilities', []))}

Generate the guide in markdown format containing the following sections:

1. **HR/Behavioral Questions (3-5 questions)**
   - Tailored to the company culture and role.
   - Include 'Intent behind the question' and 'Key points to mention in response'.

2. **Technical & Core Concepts (5 questions)**
   - Specific questions on Python, deep learning, NLP, RAG, or Flutter/mobile development depending on the job title.
   - Detailed conceptual explanation for each.

3. **Practical Coding / Implementation Challenges (2 problems)**
   - Relevant coding challenges (e.g. implementing self-attention block, mobile state-management logic, or training loop).
   - Show clean Python/Dart code outline and explanation.

4. **System Design / Architecture (2 questions)**
   - High-level system design (e.g. designing a RAG ingestion pipeline, real-time sync in mobile apps, or serving ML models at scale).
   - Key architectural components and diagrams.

Output raw markdown. Do not wrap in JSON.
"""

        try:
            markdown_content = self._llm_client.generate_text(prompt, system_prompt)
            
            # Save to reports directory
            self.settings.ensure_dirs()
            safe_company = "".join(c for c in company if c.isalnum() or c == "_").replace(" ", "_")
            safe_title = "".join(c for c in title if c.isalnum() or c == "_").replace(" ", "_")
            filename = f"interview_prep_{safe_company}_{safe_title}.md"
            output_path = self.settings.reports_dir / filename

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(markdown_content)

            self.logger.info(f"Successfully saved interview prep: {output_path}")
            return output_path

        except Exception as e:
            self.logger.error(f"Failed to generate interview prep: {e}")
            return None
