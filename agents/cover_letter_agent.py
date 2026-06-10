"""
Cover Letter Generation Agent.

Uses Gemini API (via LLMClient) to generate a tailored, professional cover letter
for a specific job, and outputs it in both TXT and PDF formats.
"""

import json
import os
from pathlib import Path
from typing import Any

from agents.base_agent import BaseAgent
from config.settings import Settings
from utils.llm_client import LLMClient

# Pre-emptively set the environment variable for WeasyPrint/Pango on macOS
os.environ["DYLD_LIBRARY_PATH"] = "/opt/homebrew/lib"


class CoverLetterAgent(BaseAgent):
    """Generates personalized cover letters matching a target job description."""

    @property
    def name(self) -> str:
        return "cover_letter"

    def __init__(self, llm_client: LLMClient) -> None:
        super().__init__()
        self._llm_client = llm_client
        self.settings = Settings()

    def generate_letter_text(self, job_data: dict[str, Any], resume_data: dict[str, Any]) -> str:
        """Use Gemini to generate a professional cover letter as text."""
        company = job_data.get("company", "Unknown Company")
        title = job_data.get("title", "Unknown Role")
        jd_analysis = job_data.get("analysis", {})

        system_prompt = (
            "You are an expert career consultant and copywriter. "
            "Generate a professional, compelling, and customized cover letter."
        )

        prompt = f"""
Write a professional cover letter for Yash Pal applying for the role "{title}" at "{company}".

Candidate Details:
- Name: Yash Pal
- Degree: B.E. Computer Science (AI & ML), University of Mumbai
- Skills: Python, PyTorch, TensorFlow, LangChain, Flutter, Dart, Firebase, Docker
- Summary of Experience & Projects:
{json.dumps(resume_data.get('projects', []), indent=2)}

Job Details:
- Role: {title}
- Company: {company}
- Job Summary: {jd_analysis.get('summary', '')}
- Key Requirements: {', '.join(jd_analysis.get('required_skills', []))}
- Responsibilities: {', '.join(jd_analysis.get('responsibilities', []))}

Guidelines:
1. Make it professional, polite, and confident (not overly boasting).
2. Write 3-4 paragraphs (approx. 250-350 words).
3. First paragraph: State the role applied for and express enthusiasm for the company.
4. Second paragraph: Highlight 1-2 key projects from the candidate's resume that match the job requirements (e.g. LLM/Agent automation, mobile Flutter apps).
5. Third paragraph: Connect the candidate's academic background (B.E. AI & ML) and tools to the company's needs.
6. Fourth paragraph: Propose next steps (call to action/interview) and express thanks.
7. Use placeholders [Date] and standard greeting format.
"""
        return self._llm_client.generate_text(prompt, system_prompt)

    def compile_to_pdf(self, letter_text: str, output_path: Path) -> None:
        """Compile the cover letter plain text into a styled PDF."""
        import weasyprint

        # Simple inline HTML/CSS layout for a clean corporate letter
        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <style>
        @page {{
            size: A4;
            margin: 1.0in;
        }}
        body {{
            font-family: 'Calibri', 'Arial', sans-serif;
            font-size: 11pt;
            color: #222;
            line-height: 1.5;
        }}
        .letter-content {{
            white-space: pre-line;
        }}
    </style>
</head>
<body>
    <div class="letter-content">
        {letter_text}
    </div>
</body>
</html>
"""
        html_doc = weasyprint.HTML(string=html_content)
        html_doc.write_pdf(target=output_path)

    def run(self, job_data: dict[str, Any], resume_data: dict[str, Any]) -> dict[str, Any]:
        """
        Generate and write cover letter in TXT and PDF.

        Args:
            job_data: Scored job listing dict with analysis.
            resume_data: Tailored resume dict.

        Returns:
            Dict containing output paths: 'txt_path' and 'pdf_path'.
        """
        company = job_data.get("company", "Unknown").replace(" ", "_")
        title = job_data.get("title", "Unknown").replace(" ", "_")
        
        # Clean filename strings
        safe_company = "".join(c for c in company if c.isalnum() or c == "_")
        safe_title = "".join(c for c in title if c.isalnum() or c == "_")
        filename_base = f"cover_letter_{safe_company}_{safe_title}"

        self.logger.info(f"Generating cover letter for {job_data.get('company')}...")
        letter_text = self.generate_letter_text(job_data, resume_data)

        # Output paths
        self.settings.ensure_dirs()
        txt_path = self.settings.reports_dir / f"{filename_base}.txt"
        pdf_path = self.settings.reports_dir / f"{filename_base}.pdf"

        # Write text version
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(letter_text)

        # Write PDF version
        try:
            self.compile_to_pdf(letter_text, pdf_path)
            self.logger.info(f"Successfully saved cover letter as TXT ({txt_path}) and PDF ({pdf_path})")
        except Exception as e:
            self.logger.error(f"Failed to generate cover letter PDF: {e}")

        return {
            "txt_path": str(txt_path),
            "pdf_path": str(pdf_path),
        }
