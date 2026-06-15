"""
Central settings for the AI Job Hunter Agent.

Loads configuration from environment variables and .env file using Pydantic Settings.
All configurable parameters live here — no magic strings scattered across modules.
"""

from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables / .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ─── Project Paths ───
    project_root: Path = Path(__file__).resolve().parent.parent
    knowledge_dir: Path = Path(__file__).resolve().parent.parent / "knowledge"
    resume_output_dir: Path = Path(__file__).resolve().parent.parent / "resume" / "output"
    reports_dir: Path = Path(__file__).resolve().parent.parent / "reports"

    # ─── Gemini AI ───
    gemini_api_key: str = ""
    gemini_model: str = "gemini-2.5-flash"

    # ─── Ollama Fallback ───
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"

    # ─── Google Sheets ───
    google_sheets_cred_path: str = "./credentials/service_account.json"
    google_sheet_id: str = ""

    # ─── Telegram ───
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""

    # ─── Application Logic ───
    max_daily_applications: int = 10
    top_k_for_llm: int = 5
    min_ats_score: int = 80
    dry_run: bool = False
    log_level: str = "INFO"

    # ─── Scraping ───
    scraper_timeout: int = 30  # seconds per request
    scraper_delay_min: float = 1.0  # min delay between requests (seconds)
    scraper_delay_max: float = 3.0  # max delay between requests (seconds)
    scraper_max_retries: int = 3
    max_jobs_per_source: int = 50  # cap per scraper to avoid runaway

    # ─── Rate Limits ───
    gemini_rpm: int = 10  # conservative free-tier RPM
    sheets_rpm: int = 60  # well under the 300/min quota

    def ensure_dirs(self) -> None:
        """Create output directories if they don't exist."""
        self.resume_output_dir.mkdir(parents=True, exist_ok=True)
        self.reports_dir.mkdir(parents=True, exist_ok=True)
