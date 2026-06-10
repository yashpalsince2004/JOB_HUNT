"""
Resume Generator.

Takes tailored resume data, renders it to an HTML template,
and uses WeasyPrint to compile it into an ATS-compliant PDF.
"""

import os
from pathlib import Path
from typing import Any

# Pre-emptively set the environment variable for WeasyPrint/Pango on macOS
os.environ["DYLD_LIBRARY_PATH"] = "/opt/homebrew/lib"

from jinja2 import Environment, FileSystemLoader
from config.settings import Settings
from utils.logger import get_logger

logger = get_logger("resume.generator")


class ResumeGenerator:
    """Renders HTML-based resumes and compiles them to PDF using WeasyPrint."""

    def __init__(self) -> None:
        self.settings = Settings()
        self.template_dir = Path(__file__).resolve().parent / "templates"
        self.env = Environment(loader=FileSystemLoader(self.template_dir))

    def generate_pdf(self, resume_data: dict[str, Any], output_filename: str) -> Path:
        """
        Compile resume data to a PDF file.

        Args:
            resume_data: Dictionary representing the tailored resume structure.
            output_filename: Output filename (e.g. 'yash_pal_stripe.pdf').

        Returns:
            Path to the generated PDF file.
        """
        # 1. Ensure output directory exists
        self.settings.ensure_dirs()
        output_path = self.settings.resume_output_dir / output_filename

        try:
            # Import WeasyPrint here (after setting DYLD_LIBRARY_PATH)
            import weasyprint

            # 2. Render Jinja2 template to HTML string
            template = self.env.get_template("resume_template.html")
            rendered_html = template.render(**resume_data)

            # 3. Compile to PDF using WeasyPrint
            logger.info(f"Compiling PDF for {output_filename}...")
            
            # We pass base_url so WeasyPrint can find resume_styles.css in the template directory
            html_doc = weasyprint.HTML(string=rendered_html, base_url=str(self.template_dir))
            html_doc.write_pdf(target=output_path)
            
            logger.info(f"Successfully generated PDF: {output_path}")
            return output_path

        except Exception as e:
            logger.error(f"Failed to generate resume PDF: {e}", exc_info=True)
            raise
