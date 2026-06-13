"""
Resume Generator.

Takes tailored resume data, renders it to a LaTeX template,
and compiles it into a professional PDF using a LaTeX engine.
"""

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader
from config.settings import Settings
from utils.logger import get_logger

logger = get_logger("resume.generator")


def escape_latex_str(text: str) -> str:
    """Escape LaTeX special characters in a string."""
    if not isinstance(text, str):
        return text
    # Map of special characters to their escaped versions
    # Backslash must be escaped first because other escapes introduce backslashes!
    latex_special = {
        '\\': r'\textbackslash{}',
        '&': r'\&',
        '%': r'\%',
        '$': r'\$',
        '#': r'\#',
        '_': r'\_',
        '{': r'\{',
        '}': r'\}',
        '~': r'\textasciitilde{}',
        '^': r'\textasciicircum{}',
    }
    # Escape backslash first
    res = text.replace('\\', latex_special['\\'])
    for char, replacement in latex_special.items():
        if char != '\\':
            res = res.replace(char, replacement)
    return res


def escape_latex_data(data: Any) -> Any:
    """Recursively escape special characters in dictionaries, lists, and strings."""
    if isinstance(data, dict):
        return {k: escape_latex_data(v) for k, v in data.items()}
    elif isinstance(data, list):
        return [escape_latex_data(item) for item in data]
    elif isinstance(data, str):
        return escape_latex_str(data)
    return data


class ResumeGenerator:
    """Renders LaTeX-based resumes and compiles them to PDF."""

    def __init__(self) -> None:
        self.settings = Settings()
        self.template_dir = Path(__file__).resolve().parent / "templates"
        
        # Configure Jinja2 environment with LaTeX-compatible delimiters
        self.env = Environment(
            loader=FileSystemLoader(self.template_dir),
            block_start_string='%-',
            block_end_string='-%',
            variable_start_string='<<',
            variable_end_string='>>',
            comment_start_string='%#',
            comment_end_string='#%'
        )

    def generate_pdf(self, resume_data: dict[str, Any], output_filename: str) -> Path:
        """
        Compile resume data to a LaTeX file and then compile to PDF.

        Args:
            resume_data: Dictionary representing the tailored resume structure.
            output_filename: Output filename (e.g. 'yash_pal_stripe.pdf').

        Returns:
            Path to the generated PDF file.
        """
        self.settings.ensure_dirs()
        output_path = self.settings.resume_output_dir / output_filename
        tex_output_path = output_path.with_suffix(".tex")

        try:
            # 1. Escape LaTeX special characters recursively
            escaped_data = escape_latex_data(resume_data)

            # 2. Render LaTeX template to string
            template = self.env.get_template("resume_template.tex")
            rendered_tex = template.render(**escaped_data)

            # 3. Write TeX file
            with open(tex_output_path, "w", encoding="utf-8") as f:
                f.write(rendered_tex)
            logger.info(f"Saved LaTeX source to: {tex_output_path}")

            # 4. Find available LaTeX compiler
            compiler = None
            for c in ["tectonic", "xelatex", "pdflatex"]:
                if shutil.which(c):
                    compiler = c
                    break

            if not compiler:
                msg = (
                    f"No LaTeX compiler (tectonic, xelatex, pdflatex) found on system. "
                    f"The LaTeX source has been saved to {tex_output_path}. "
                    "You can compile this manually or install tectonic via: brew install tectonic"
                )
                logger.warning(msg)
                raise FileNotFoundError(
                    f"No LaTeX compiler found to generate PDF. TeX source saved at: {tex_output_path}. "
                    "Please install tectonic ('brew install tectonic') to compile automatically."
                )

            # 5. Compile PDF
            logger.info(f"Compiling PDF using {compiler} for {output_filename}...")
            if compiler == "tectonic":
                cmd = ["tectonic", "-o", str(self.settings.resume_output_dir), str(tex_output_path)]
            else:
                cmd = [
                    compiler,
                    "-interaction=nonstopmode",
                    f"-output-directory={self.settings.resume_output_dir}",
                    str(tex_output_path)
                ]

            # Clean DYLD_LIBRARY_PATH from env to prevent dynamic linker errors in tectonic/xelatex
            sub_env = os.environ.copy()
            if "DYLD_LIBRARY_PATH" in sub_env:
                del sub_env["DYLD_LIBRARY_PATH"]

            subprocess.run(cmd, capture_output=True, text=True, check=True, env=sub_env)
            logger.info(f"Successfully generated PDF: {output_path}")

            # Cleanup auxiliary files created by pdflatex/xelatex
            if compiler != "tectonic":
                for ext in [".aux", ".log", ".out"]:
                    aux_file = output_path.with_suffix(ext)
                    if aux_file.exists():
                        aux_file.unlink()

            return output_path

        except subprocess.CalledProcessError as e:
            logger.error(f"LaTeX compiler failed: {e.stdout}\n{e.stderr}", exc_info=True)
            raise RuntimeError(f"LaTeX compiler failed: {e.stderr or e.stdout}") from e
        except Exception as e:
            logger.error(f"Failed to generate resume PDF: {e}", exc_info=True)
            raise
