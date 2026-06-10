"""
Recruiter Discovery and Outreach Agent.

Generates highly personalized outreach templates (LinkedIn / Email)
targeting recruiters and hiring managers at the respective companies.
"""

from typing import Any

from agents.base_agent import BaseAgent
from config.settings import Settings
from utils.llm_client import LLMClient


class RecruiterAgent(BaseAgent):
    """Generates personalized outreach messages for recruiters using Gemini."""

    @property
    def name(self) -> str:
        return "recruiter_outreach"

    def __init__(self, llm_client: LLMClient) -> None:
        super().__init__()
        self._llm_client = llm_client
        self.settings = Settings()

    def run(self, job_data: dict[str, Any]) -> dict[str, str]:
        """
        Generate outreach message templates for a job listing.

        Args:
            job_data: A job listing dictionary containing company, title, location, and analysis.

        Returns:
            A dictionary containing 'linkedin_template' and 'email_template'.
        """
        company = job_data.get("company", "Unknown Company")
        title = job_data.get("title", "Unknown Role")
        jd_analysis = job_data.get("analysis", {})
        
        self.logger.info(f"Generating recruiter outreach templates for {company} — {title}...")

        system_prompt = (
            "You are a professional networking coach and technical recruiter. "
            "Write highly effective, short, and customized cold outreach messages "
            "for LinkedIn and email."
        )

        prompt = f"""
Write cold outreach messages for Yash Pal (B.E. CS AI/ML, University of Mumbai) to send to recruiters at "{company}" for the role "{title}".

Job Summary:
{jd_analysis.get('summary', '')}

Candidate Strengths:
- Deep learning, PyTorch, generative AI integration (Gemini, LangChain).
- Mobile development using Flutter & Dart.
- Built fully automated job hunting system.

Generate two templates:
1. **LinkedIn Message (strictly under 300 characters for connection requests)**
   - Must be punchy, stating interest, degree background, and matching skills.
   - Example: 'Hi [Recruiter Name], I saw the [Role] position at [Company]. I'm an AI/ML grad from Mumbai Uni with experience in PyTorch/Flutter. I'd love to connect and share my portfolio. Thanks, Yash.'
2. **Cold Email (approx. 100-150 words)**
   - A short, professional pitch with a clear call to action and placeholders.

Return the response as a JSON object with keys: "linkedin_template" and "email_template".
"""
        try:
            outreach = self._llm_client.generate_json(prompt, system_prompt)
            # Basic validation
            if "linkedin_template" not in outreach or "email_template" not in outreach:
                raise ValueError("LLM response missing outreach template keys.")
            return outreach
        except Exception as e:
            self.logger.error(f"Failed to generate outreach templates: {e}")
            return {
                "linkedin_template": f"Hi! I am interested in the {title} role at {company}. I have a B.E. in CS (AI & ML) and experience in Flutter/PyTorch. I would love to connect. Best, Yash Pal.",
                "email_template": f"Dear Recruiting Team,\n\nI am writing to express my interest in the {title} position at {company}.\n\nBest regards,\nYash Pal"
            }
