"""
Telegram Interactive Bot.

Provides interactive commands to query job hunting stats and status.
Runs as a separate background process.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# Set library path for WeasyPrint
os.environ["DYLD_LIBRARY_PATH"] = "/opt/homebrew/lib"

load_dotenv()

from telegram import Update

from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
)
from config.settings import Settings
from sheets.client import SheetsClient
from utils.logger import setup_logging, get_logger

logger = get_logger("telegram.bot")


class JobHunterBot:
    """Telegram Bot wrapper class."""

    def __init__(self) -> None:
        self.settings = Settings()
        self._token = self.settings.telegram_bot_token
        self._sheets_client = None

        if self.settings.google_sheet_id and Path(self.settings.google_sheets_cred_path).exists():
            try:
                self._sheets_client = SheetsClient(
                    cred_path=self.settings.google_sheets_cred_path,
                    sheet_id=self.settings.google_sheet_id
                )
                self._sheets_client.initialize()
            except Exception as e:
                logger.error(f"Failed to initialize SheetsClient for bot: {e}")

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler for /start command."""
        if not update.effective_message:
            return
        user = update.effective_user
        welcome_text = (
            f"Hello {user.first_name if user else 'Yash'}!\n"
            f"Welcome to AI Job Hunter Agent Bot.\n\n"
            f"Available Commands:\n"
            f"/summary - Get daily/weekly stats\n"
            f"/jobs - List top matching jobs prepared today\n"
            f"/status - Check pipeline configurations and status"
        )
        await update.effective_message.reply_text(welcome_text)

    async def summary(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler for /summary command."""
        if not update.effective_message:
            return

        if not self._sheets_client:
            await update.effective_message.reply_text("Google Sheets connection not initialized.")
            return

        try:
            records = self._sheets_client.get_sheet_records("DailySummary")
            if not records:
                await update.effective_message.reply_text("No daily summary records found.")
                return

            # Show last 5 summaries
            latest = records[-5:]
            text = "📈 <b>Recent Daily Summaries:</b>\n\n"
            for r in reversed(latest):
                text += (
                    f"📅 Date: {r.get('date')}\n"
                    f"🔍 Scraped: {r.get('jobs_scraped')} | 🆕 New: {r.get('jobs_new')}\n"
                    f"🎯 Matches: {r.get('jobs_relevant')} | 💼 Prep: {r.get('applications_prepared')}\n"
                    f"----------------------\n"
                )
            await update.effective_message.reply_html(text)
        except Exception as e:
            logger.error(f"Error in summary command: {e}")
            await update.effective_message.reply_text("Failed to retrieve daily summaries.")

    async def jobs(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler for /jobs command."""
        if not update.effective_message:
            return

        if not self._sheets_client:
            await update.effective_message.reply_text("Google Sheets connection not initialized.")
            return

        try:
            records = self._sheets_client.get_sheet_records("Applications")
            if not records:
                await update.effective_message.reply_text("No applications prepared yet.")
                return

            # Get latest 5 prepared applications
            latest = [r for r in records if r.get("status") == "prepared"][-5:]
            if not latest:
                await update.effective_message.reply_text("No recently prepared applications found.")
                return

            text = "💼 <b>Latest Prepared Applications:</b>\n\n"
            for r in reversed(latest):
                text += (
                    f"🏢 <b>{r.get('company')}</b> — {r.get('title')}\n"
                    f"🔥 ATS Score: <b>{r.get('ats_score')}/100</b>\n"
                    f"🔗 <a href='{r.get('url')}'>Job URL</a>\n\n"
                )
            await update.effective_message.reply_html(text, disable_web_page_preview=True)
        except Exception as e:
            logger.error(f"Error in jobs command: {e}")
            await update.effective_message.reply_text("Failed to retrieve jobs.")

    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handler for /status command."""
        if not update.effective_message:
            return
        sheet_status = "Connected" if self._sheets_client else "Disconnected"
        env_status = "Configured" if self.settings.gemini_api_key else "Missing API Key"
        text = (
            f"🤖 <b>System Health Check:</b>\n\n"
            f"📊 Sheets Integration: <b>{sheet_status}</b>\n"
            f"🧠 AI Engine (Gemini): <b>{env_status}</b>\n"
            f"🎯 Min ATS Score Threshold: <b>{self.settings.min_ats_score}</b>\n"
            f"💼 Max Daily Applications Limit: <b>{self.settings.max_daily_applications}</b>"
        )
        await update.effective_message.reply_html(text)

    def run(self) -> None:
        """Start the Telegram bot event loop."""
        if not self._token:
            logger.error("No Telegram Bot Token provided. Bot cannot start.")
            sys.exit(1)

        logger.info("Starting Telegram Bot listener...")
        app = Application.builder().token(self._token).build()

        # Command handlers
        app.add_handler(CommandHandler("start", self.start))
        app.add_handler(CommandHandler("summary", self.summary))
        app.add_handler(CommandHandler("jobs", self.jobs))
        app.add_handler(CommandHandler("status", self.status))

        # Start the bot
        app.run_polling()


if __name__ == "__main__":
    setup_logging(level="INFO")
    bot = JobHunterBot()
    try:
        bot.run()
    except KeyboardInterrupt:
        logger.info("Bot execution terminated by user.")
