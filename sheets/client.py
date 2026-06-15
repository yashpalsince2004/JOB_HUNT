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
  6. TopJobs      — Strongest matching jobs of each day
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
        "date", "scraped", "deduped", "rejected_role", "rejected_location",
        "rejected_experience", "queued_gemini", "ats_qualified", "top_jobs_selected",
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
    "TopJobs": [
        "Company", "Role", "Location", "Role Score", "Location Score", "Skill Score", "Company Score", "Experience Score", "Freshness Score", "ATS Score", "Final Score", "Apply URL", "Status", "Reason"
    ],
    "RejectedJobs": [
        "Company", "Role", "Reason", "Location", "Experience"
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
            # Status is the 9th column (index 9 in 1-based index)
            # Find the index of "status" in the headers
            status_col = _SHEET_SCHEMAS["Jobs"].index("status") + 1
            ws.update_cell(cell.row, status_col, status)
            return True
        logger.warning(f"Job ID not found: {job_id}")
        return False

    # ─── TopJobs Sheet ───

    def update_top_jobs_sheet(self, new_jobs: list[dict[str, Any]]) -> None:
        """
        Merge new jobs with existing top jobs, sort by final score (job_score) descending,
        and rewrite the TopJobs worksheet to keep it perfectly sorted.
        """
        ws = self._get_sheet("TopJobs")
        headers = _SHEET_SCHEMAS["TopJobs"]
        
        # 1. Fetch existing records
        rate_limiter.wait_sync("sheets")
        existing_records = ws.get_all_records()
        
        # Map existing records back to standard dictionary format (lowercase keys)
        merged_jobs = []
        seen_urls = set()
        
        header_map = {
            "Company": "company",
            "Role": "title",
            "Location": "location",
            "Role Score": "role_score",
            "Location Score": "location_score",
            "Skill Score": "skill_score",
            "Company Score": "company_priority",
            "Experience Score": "experience_score",
            "Freshness Score": "freshness_score",
            "ATS Score": "ats_score",
            "Final Score": "job_score",
            "Apply URL": "url",
            "Status": "status",
            "Reason": "rejection_reason"
        }
        
        for rec in existing_records:
            job_dict = {}
            for k, v in rec.items():
                std_key = header_map.get(k)
                if std_key:
                    job_dict[std_key] = v
            url = job_dict.get("url")
            if url:
                merged_jobs.append(job_dict)
                seen_urls.add(url)
                
        # 2. Add new jobs if not already present
        for job in new_jobs:
            url = job.get("url")
            if url and url not in seen_urls:
                merged_jobs.append(job)
                seen_urls.add(url)
                
        # 3. Sort descending by job_score (Final Score)
        def get_score(j):
            try:
                return float(j.get("job_score", 0.0))
            except (ValueError, TypeError):
                return 0.0
                
        merged_jobs.sort(key=get_score, reverse=True)
        
        # 4. Clear and rewrite
        rate_limiter.wait_sync("sheets")
        ws.clear()
        rate_limiter.wait_sync("sheets")
        ws.append_row(headers, value_input_option=ValueInputOption.raw)
        
        rows = []
        for job in merged_jobs:
            # Rejection reason could be score breakdown or actual reject reason
            reason_text = job.get("rejection_reason", "")
            if not reason_text:
                reason_text = job.get("score_breakdown", "")

            row = [
                str(job.get("company", "")),
                str(job.get("title", "")),
                str(job.get("location", "")),
                str(job.get("role_score", 0.0)),
                str(job.get("location_score", 0.0)),
                str(job.get("skill_score", 0.0)),
                str(job.get("company_priority", 70)),
                str(job.get("experience_score", 0.0)),
                str(job.get("freshness_score", 0.0)),
                str(job.get("ats_score", 0.0)),
                str(job.get("job_score", 0.0)),
                str(job.get("url", "")),
                str(job.get("status", "")),
                str(reason_text)
            ]
            rows.append(row)
            
        if rows:
            rate_limiter.wait_sync("sheets")
            ws.append_rows(rows, value_input_option=ValueInputOption.raw)
            logger.info(f"TopJobs sheet rewritten with {len(rows)} sorted jobs.")

    # ─── RejectedJobs Sheet ───

    def add_rejected_jobs(self, rejected_jobs: list[dict[str, Any]]) -> None:
        """Add rejected jobs to the RejectedJobs sheet."""
        if not rejected_jobs:
            return
        ws = self._get_sheet("RejectedJobs")
        
        rows = []
        for job in rejected_jobs:
            # Rejection reason could be score breakdown or actual reject reason
            reason_text = job.get("rejection_reason", "")
            if not reason_text:
                reason_text = job.get("score_breakdown", "")

            rows.append([
                str(job.get("company", "")),
                str(job.get("title", "")),
                str(reason_text),
                str(job.get("location", "")),
                str(job.get("experience", ""))
            ])
            
        if rows:
            rate_limiter.wait_sync("sheets")
            ws.append_rows(rows, value_input_option=ValueInputOption.raw)
            logger.info(f"Appended {len(rows)} rejected jobs to RejectedJobs sheet.")

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
        scraped: int,
        deduped: int,
        rejected_role: int,
        rejected_location: int,
        rejected_experience: int,
        queued_gemini: int,
        ats_qualified: int,
        top_jobs_selected: int,
    ) -> None:
        """Log today's run summary with refined metrics."""
        ws = self._get_sheet("DailySummary")
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        row = [
            today, scraped, deduped, rejected_role, rejected_location,
            rejected_experience, queued_gemini, ats_qualified, top_jobs_selected
        ]
        rate_limiter.wait_sync("sheets")
        ws.append_row(row, value_input_option=ValueInputOption.raw)
        logger.info(f"Daily summary logged: {scraped} scraped, {deduped} deduped, {top_jobs_selected} top jobs selected")

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
