"""
Google Sheets client for the AI Job Hunter Agent.

Wraps gspread to provide typed methods for all sheet operations.
Auto-creates required worksheets on first run.

Sheets structure:
  1. Jobs         — All scraped job listings
  2. Applications — Jobs that passed ATS threshold
  3. DailySummary — Per-day aggregated stats
  4. SkillGaps    — Most demanded skills across all JDs
  5. Interviews   — Interview tracking
"""

from datetime import datetime, timezone
from typing import Any

import gspread
from gspread.utils import ValueInputOption
from google.oauth2.service_account import Credentials

from utils.logger import get_logger
from utils.rate_limiter import rate_limiter

logger = get_logger("sheets")

# Google API scopes needed
_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# Sheet schemas (header rows)
_SHEET_SCHEMAS = {
    "Jobs": [
        "job_id", "company", "title", "location", "url",
        "source", "posted_date", "scraped_at", "status",
        "role_category", "job_score", "ats_score", "company_priority",
        "experience", "salary", "skills", "employment_type", "remote_status",
        "salary_min", "salary_max", "salary_currency", "salary_period",
    ],
    "Applications": [
        "job_id", "company", "title", "url", "ats_score",
        "resume_path", "cover_letter_path", "applied_at", "status",
    ],
    "DailySummary": [
        "date", "jobs_scraped", "jobs_new", "jobs_relevant",
        "jobs_above_ats", "applications_prepared", "skipped",
    ],
    "SkillGaps": [
        "skill", "demand_count", "in_resume", "last_updated",
    ],
    "Interviews": [
        "job_id", "company", "role", "stage",
        "scheduled_date", "prep_path", "result", "notes",
    ],
    "AnalyticsCompanies": [
        "Company", "Role", "Location", "Experience", "Job Score", "ATS Score", "Posted Date", "Apply URL", "Status"
    ],
}


class SheetsClient:
    """
    Google Sheets client for reading/writing job hunt data.

    Usage:
        client = SheetsClient(cred_path="./creds.json", sheet_id="abc123")
        client.initialize()
        client.add_jobs([...])
    """

    def __init__(self, cred_path: str, sheet_id: str) -> None:
        self._cred_path = cred_path
        self._sheet_id = sheet_id
        self._gc: gspread.Client | None = None
        self._spreadsheet: gspread.Spreadsheet | None = None
        self._worksheets: dict[str, gspread.Worksheet] = {}

    def initialize(self) -> None:
        """Authenticate and open the spreadsheet. Create missing sheets."""
        logger.info("Connecting to Google Sheets...")
        creds = Credentials.from_service_account_file(self._cred_path, scopes=_SCOPES)
        self._gc = gspread.authorize(creds)
        self._spreadsheet = self._gc.open_by_key(self._sheet_id)
        self._ensure_sheets()
        logger.info(f"Connected to spreadsheet: {self._spreadsheet.title}")

    def _ensure_sheets(self) -> None:
        """Create any missing worksheets with their header rows."""
        if self._spreadsheet is None:
            raise ValueError("Spreadsheet is not initialized. Call initialize() first.")
        existing = {ws.title: ws for ws in self._spreadsheet.worksheets()}

        for sheet_name, headers in _SHEET_SCHEMAS.items():
            if sheet_name in existing:
                self._worksheets[sheet_name] = existing[sheet_name]
                logger.debug(f"Sheet '{sheet_name}' already exists")
            else:
                rate_limiter.wait_sync("sheets")
                ws = self._spreadsheet.add_worksheet(
                    title=sheet_name, rows=1000, cols=len(headers)
                )
                rate_limiter.wait_sync("sheets")
                ws.append_row(headers, value_input_option=ValueInputOption.raw)
                self._worksheets[sheet_name] = ws
                logger.info(f"Created sheet '{sheet_name}' with headers")

    def _get_sheet(self, name: str) -> gspread.Worksheet:
        """Get a worksheet by name."""
        if name not in self._worksheets:
            raise ValueError(f"Unknown sheet: {name}. Available: {list(self._worksheets.keys())}")
        return self._worksheets[name]

    # ─── Jobs Sheet ───

    def get_all_job_urls(self) -> set[str]:
        """Get all existing job URLs for deduplication."""
        rate_limiter.wait_sync("sheets")
        ws = self._get_sheet("Jobs")
        records = ws.get_all_records()
        return {str(r.get("url", "")) for r in records if r.get("url")}

    def get_all_job_ids(self) -> set[str]:
        """Get all existing job IDs for deduplication."""
        rate_limiter.wait_sync("sheets")
        ws = self._get_sheet("Jobs")
        records = ws.get_all_records()
        return {str(r.get("job_id", "")) for r in records if r.get("job_id")}

    def add_jobs(self, jobs: list[dict[str, Any]]) -> int:
        """
        Append new job listings to the Jobs sheet.

        Args:
            jobs: List of job dicts matching the Jobs schema.

        Returns:
            Number of jobs added.
        """
        if not jobs:
            return 0

        ws = self._get_sheet("Jobs")
        headers = _SHEET_SCHEMAS["Jobs"]
        rows = []
        for job in jobs:
            row = [str(job.get(h, "")) for h in headers]
            rows.append(row)

        rate_limiter.wait_sync("sheets")
        ws.append_rows(rows, value_input_option=ValueInputOption.raw)
        logger.info(f"Added {len(rows)} jobs to Jobs sheet")
        return len(rows)

    def add_analytics_company_jobs(self, jobs: list[dict[str, Any]]) -> int:
        """
        Append new job listings to the AnalyticsCompanies sheet.

        Args:
            jobs: List of job dicts matching the AnalyticsCompanies schema.

        Returns:
            Number of jobs added.
        """
        if not jobs:
            return 0

        ws = self._get_sheet("AnalyticsCompanies")
        headers = _SHEET_SCHEMAS["AnalyticsCompanies"]
        rows = []
        for job in jobs:
            row = [str(job.get(h, "")) for h in headers]
            rows.append(row)

        rate_limiter.wait_sync("sheets")
        ws.append_rows(rows, value_input_option=ValueInputOption.raw)
        logger.info(f"Added {len(rows)} jobs to AnalyticsCompanies sheet")
        return len(rows)

    def update_job_status(self, job_id: str, status: str) -> bool:
        """Update the status of a job by its job_id."""
        rate_limiter.wait_sync("sheets")
        ws = self._get_sheet("Jobs")
        cell = ws.find(job_id)
        if cell:
            # Status is the last column
            status_col = len(_SHEET_SCHEMAS["Jobs"])
            ws.update_cell(cell.row, status_col, status)
            return True
        logger.warning(f"Job ID not found: {job_id}")
        return False

    # ─── Applications Sheet ───

    def add_application(self, application: dict[str, Any]) -> None:
        """Add an application record."""
        ws = self._get_sheet("Applications")
        headers = _SHEET_SCHEMAS["Applications"]
        row = [str(application.get(h, "")) for h in headers]
        rate_limiter.wait_sync("sheets")
        ws.append_row(row, value_input_option=ValueInputOption.raw)
        logger.info(f"Added application for {application.get('company', 'Unknown')}")

    def get_applied_urls(self) -> set[str]:
        """Get URLs of all previously applied jobs."""
        rate_limiter.wait_sync("sheets")
        ws = self._get_sheet("Applications")
        records = ws.get_all_records()
        return {str(r.get("url", "")) for r in records if r.get("url")}

    # ─── Daily Summary Sheet ───

    def add_daily_summary(
        self,
        jobs_scraped: int,
        jobs_new: int,
        jobs_relevant: int,
        jobs_above_ats: int,
        applications_prepared: int,
        skipped: int,
    ) -> None:
        """Log today's run summary."""
        ws = self._get_sheet("DailySummary")
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        row = [today, jobs_scraped, jobs_new, jobs_relevant,
               jobs_above_ats, applications_prepared, skipped]
        rate_limiter.wait_sync("sheets")
        ws.append_row(row, value_input_option=ValueInputOption.raw)
        logger.info(f"Daily summary logged: {jobs_scraped} scraped, {jobs_new} new")

    # ─── Skill Gaps Sheet ───

    def update_skill_gaps(self, skill_counts: dict[str, int], resume_skills: set[str]) -> None:
        """
        Update the skill demand counts.

        Args:
            skill_counts: Mapping of skill name → demand count.
            resume_skills: Set of skills currently in Yash's resume.
        """
        ws = self._get_sheet("SkillGaps")
        now = datetime.now(timezone.utc).strftime("%Y-%m-%d")

        # Clear old data and rewrite (simpler than individual updates)
        rate_limiter.wait_sync("sheets")
        ws.clear()
        rate_limiter.wait_sync("sheets")
        ws.append_row(_SHEET_SCHEMAS["SkillGaps"], value_input_option=ValueInputOption.raw)

        rows = []
        for skill, count in sorted(skill_counts.items(), key=lambda x: -x[1]):
            in_resume = "Yes" if skill.lower() in {s.lower() for s in resume_skills} else "No"
            rows.append([skill, count, in_resume, now])

        if rows:
            rate_limiter.wait_sync("sheets")
            ws.append_rows(rows, value_input_option=ValueInputOption.raw)
            logger.info(f"Updated {len(rows)} skill gap entries")

    # ─── Interviews Sheet ───

    def add_interview(self, interview: dict[str, Any]) -> None:
        """Add an interview tracking record."""
        ws = self._get_sheet("Interviews")
        headers = _SHEET_SCHEMAS["Interviews"]
        row = [str(interview.get(h, "")) for h in headers]
        rate_limiter.wait_sync("sheets")
        ws.append_row(row, value_input_option=ValueInputOption.raw)

    # ─── Utility Methods ───

    def get_sheet_records(self, sheet_name: str) -> list[dict[str, Any]]:
        """Get all records from a named sheet as list of dicts."""
        rate_limiter.wait_sync("sheets")
        ws = self._get_sheet(sheet_name)
        return ws.get_all_records()

    def test_connection(self) -> bool:
        """Test that we can connect and read from the spreadsheet."""
        try:
            self.initialize()
            if self._spreadsheet is None:
                raise ValueError("Spreadsheet was not initialized correctly.")
            sheet_names = [ws.title for ws in self._spreadsheet.worksheets()]
            logger.info(f"Connection OK. Sheets: {sheet_names}")
            return True
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
