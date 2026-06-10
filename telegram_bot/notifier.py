"""
Telegram Notifier.

Sends real-time daily reports and job card alerts to Yash Pal's Telegram chat.
Uses direct HTTP POST requests to Telegram Bot API for lightweight, robust delivery.
"""

import html
import httpx
from typing import Any

from config.settings import Settings
from utils.logger import get_logger

logger = get_logger("telegram.notifier")


class TelegramNotifier:
    """Sends notifications to a Telegram chat via the Bot API."""

    def __init__(self, token: str | None = None, chat_id: str | None = None) -> None:
        settings = Settings()
        self._token = token or settings.telegram_bot_token
        self._chat_id = chat_id or settings.telegram_chat_id
        self._enabled = bool(self._token and self._chat_id)

        if not self._enabled:
            logger.warning("Telegram Bot Token or Chat ID not configured. Notifier disabled.")

    def _send_message(self, text: str) -> bool:
        """Helper to send HTML-formatted message via POST request."""
        if not self._enabled:
            logger.info(f"[Telegram Notifier (Disabled)]: {text[:100]}...")
            return False

        url = f"https://api.telegram.org/bot{self._token}/sendMessage"
        payload = {
            "chat_id": self._chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": True,
        }

        try:
            response = httpx.post(url, json=payload, timeout=10.0)
            response.raise_for_status()
            return True
        except Exception as e:
            logger.error(f"Failed to send Telegram message: {e}")
            return False

    def send_daily_summary(
        self,
        jobs_scraped: int,
        jobs_new: int,
        jobs_relevant: int,
        jobs_above_ats: int,
        applications_prepared: int,
    ) -> None:
        """Send a structured daily summary report."""
        # We need datetime, let's import it locally
        from datetime import datetime as dt
        today = dt.now().strftime("%B %d, %Y")

        message = (
            f"🤖 <b>AI Job Hunter Daily Report</b>\n"
            f"📅 <i>{today}</i>\n\n"
            f"🔍 Jobs Scraped: <b>{jobs_scraped}</b>\n"
            f"🆕 New Unique: <b>{jobs_new}</b>\n"
            f"🎯 Matching Profile: <b>{jobs_relevant}</b>\n"
            f"📈 Scored Above ATS: <b>{jobs_above_ats}</b>\n"
            f"💼 Packages Prepared: <b>{applications_prepared}</b>\n\n"
            f"Check Google Sheets for full details!"
        )
        self._send_message(message)

    def send_job_card(self, job_data: dict[str, Any]) -> None:
        """Send an alert card for a prepared job application package."""
        company = html.escape(job_data.get("company", "Unknown"))
        title = html.escape(job_data.get("title", "Unknown"))
        location = html.escape(job_data.get("location", "Unknown"))
        url = job_data.get("url", "#")
        ats_score = job_data.get("ats_score", 0)

        # Highlight status using emojis
        score_emoji = "🔥" if ats_score >= 85 else "✅"

        message = (
            f"🎯 <b>New Job Application Ready!</b>\n\n"
            f"🏢 <b>Company:</b> {company}\n"
            f"💼 <b>Role:</b> {title}\n"
            f"📍 <b>Location:</b> {location}\n"
            f"{score_emoji} <b>ATS Score:</b> <b>{ats_score}/100</b>\n\n"
            f"🔗 <a href='{url}'>View Job Posting</a>\n"
            f"📄 <i>Resume & cover letter prepared in reports directory.</i>"
        )
        self._send_message(message)

    def send_error_alert(self, error_message: str) -> None:
        """Send a critical pipeline failure notification."""
        from datetime import datetime as dt
        now = dt.now().strftime("%Y-%m-%d %H:%M:%S")

        message = (
            f"⚠️ <b>Job Hunter Pipeline Alert!</b>\n"
            f"⏰ Time: {now}\n\n"
            f"❌ <b>Error:</b>\n"
            f"<code>{html.escape(error_message)}</code>"
        )
        self._send_message(message)
