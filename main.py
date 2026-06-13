"""
AI Job Hunter Agent v3.0 — Main Pipeline Orchestrator.

Integrates all agents and scrapers to automate daily job hunts.
Usage:
    python main.py --mode=daily
    python main.py --mode=dry-run
"""

import argparse
from datetime import datetime, timezone
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Set homebrew library path for WeasyPrint before importing
os.environ["DYLD_LIBRARY_PATH"] = "/opt/homebrew/lib"

# Load environment variables from .env if present
load_dotenv()

from config.settings import Settings
from utils.logger import setup_logging, get_logger
from utils.llm_client import LLMClient
from sheets.client import SheetsClient
from resume.generator import ResumeGenerator
from telegram_bot.notifier import TelegramNotifier
from agents import (
    ScraperAgent,
    DedupAgent,
    RelevanceAgent,
    JDAnalysisAgent,
    ATSScoringAgent,
    ResumeAgent,
    CoverLetterAgent,
    InterviewAgent,
    RecruiterAgent,
    SkillGapAgent,
)

logger = get_logger("main")


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="AI Job Hunter Agent Pipeline")
    parser.add_argument(
        "--mode",
        choices=["daily", "dry-run", "scrape-only"],
        default="dry-run",
        help="Pipeline execution mode. daily runs and saves; dry-run processes but does not save; scrape-only runs only scrapers.",
    )
    parser.add_argument(
        "--log-level",
        default="INFO",
        help="Logging level (DEBUG, INFO, WARNING, ERROR)",
    )
    return parser.parse_args()


def run_pipeline(mode: str) -> None:
    """Execute the job hunting pipeline stages."""
    settings = Settings()
    settings.ensure_dirs()

    # Initialize Telegram Notifier
    notifier = TelegramNotifier()

    # 1. Sheets Client Setup
    sheets_client = None
    is_dry_run = mode == "dry-run" or settings.dry_run
    
    cred_file = Path(settings.google_sheets_cred_path)
    if not is_dry_run and cred_file.exists() and settings.google_sheet_id:
        try:
            sheets_client = SheetsClient(
                cred_path=str(cred_file),
                sheet_id=settings.google_sheet_id
            )
            sheets_client.initialize()
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets client: {e}")
            logger.warning("Falling back to dry-run mode (local results only).")
            is_dry_run = True
    else:
        if not is_dry_run:
            logger.warning(
                f"Google Sheets credentials or ID missing (Credentials file exist: {cred_file.exists()}, "
                f"Sheet ID: {'set' if settings.google_sheet_id else 'missing'}). "
                "Running in dry-run mode."
            )
            is_dry_run = True

    # 2. Stage 1: Scrape
    logger.info("--- Stage 1: Scraping Jobs ---")
    scraper = ScraperAgent()
    scraped_jobs = scraper.execute(None)
    logger.info(f"Scraped {len(scraped_jobs)} raw job listings.")

    if mode == "scrape-only":
        logger.info("Scrape-only mode requested. Terminating pipeline.")
        for idx, job in enumerate(scraped_jobs[:20], 1):
            print(f"{idx}. {job}")
        return

    # 3. Stage 2: Deduplication
    logger.info("--- Stage 2: Deduplicating Jobs ---")
    deduper = DedupAgent(sheets_client=sheets_client)
    unique_jobs = deduper.execute(scraped_jobs)
    logger.info(f"Deduplication left {len(unique_jobs)} new unique jobs.")

    # 4. Stage 3: Relevance Filtering
    logger.info("--- Stage 3: Relevance Filtering ---")
    relevance_agent = RelevanceAgent()
    relevant_jobs = relevance_agent.execute(unique_jobs)
    logger.info(f"Relevance filtering left {len(relevant_jobs)} matching jobs.")

    if not relevant_jobs:
        logger.info("No relevant matching jobs found today.")
        if not is_dry_run and sheets_client:
            try:
                sheets_client.add_daily_summary(
                    jobs_scraped=len(scraped_jobs),
                    jobs_new=len(unique_jobs),
                    jobs_relevant=0,
                    jobs_above_ats=0,
                    applications_prepared=0,
                    skipped=len(unique_jobs),
                )
            except Exception as e:
                logger.error(f"Failed to log daily summary: {e}")
        
        # Notify daily stats even if zero
        notifier.send_daily_summary(
            jobs_scraped=len(scraped_jobs),
            jobs_new=len(unique_jobs),
            jobs_relevant=0,
            jobs_above_ats=0,
            applications_prepared=0,
        )
        logger.info("Pipeline execution completed successfully.")
        return

    # Log summary of matched jobs
    logger.info(f"Summary of matched jobs:")
    for idx, job in enumerate(relevant_jobs, 1):
        logger.info(f"  {idx}. {job.company} - {job.title} ({job.location}) -> {job.url}")
        # Send special Telegram alert for High Priority AI Jobs (job_score >= 85)
        if job.job_score >= 85:
            try:
                notifier.send_premium_alert(job.to_dict())
            except Exception as e:
                logger.error(f"Failed to send high-priority Telegram alert: {e}")

    # Write matches to sheets if not dry-run
    if not is_dry_run and sheets_client:
        logger.info("--- Storing matched jobs to Google Sheets ---")
        job_dicts = [job.to_dict() for job in relevant_jobs]
        sheets_client.add_jobs(job_dicts)

    # 5. Initialize LLM Client for AI analysis
    llm_client = None
    if settings.gemini_api_key:
        try:
            llm_client = LLMClient(api_key=settings.gemini_api_key, model=settings.gemini_model)
        except Exception as e:
            logger.warning(f"Failed to initialize LLM client: {e}. AI processing will be skipped.")
    else:
        logger.warning("GEMINI_API_KEY is missing. Skipping AI-assisted JD analysis, scoring, and tailoring.")

    if not llm_client:
        logger.info("No LLM client available. Ending pipeline.")
        if not is_dry_run and sheets_client:
            try:
                # Store target Indian AI company jobs (without ATS score since LLM is missing)
                target_indian_companies = ["quantiphi", "fractal", "tiger analytics", "tredence", "latentview", "mu sigma", "musigma", "nielseniq", "nielsen", "course5", "gramener", "exl"]
                indian_ai_jobs = []
                for job in relevant_jobs:
                    comp_name = job.company.lower()
                    if any(tic in comp_name for tic in target_indian_companies):
                        indian_ai_jobs.append({
                            "Company": job.company,
                            "Role": job.title,
                            "Location": job.location,
                            "Experience": job.experience,
                            "Job Score": job.job_score,
                            "ATS Score": 0.0,
                            "Posted Date": job.posted_date,
                            "Apply URL": job.url,
                            "Status": job.status
                        })
                if indian_ai_jobs:
                    logger.info(f"Writing {len(indian_ai_jobs)} target Indian AI company jobs to AnalyticsCompanies sheet")
                    sheets_client.add_analytics_company_jobs(indian_ai_jobs)

                sheets_client.add_daily_summary(
                    jobs_scraped=len(scraped_jobs),
                    jobs_new=len(unique_jobs),
                    jobs_relevant=len(relevant_jobs),
                    jobs_above_ats=0,
                    applications_prepared=0,
                    skipped=len(unique_jobs) - len(relevant_jobs),
                )
            except Exception as e:
                logger.error(f"Failed to log daily summary: {e}")
        
        notifier.send_daily_summary(
            jobs_scraped=len(scraped_jobs),
            jobs_new=len(unique_jobs),
            jobs_relevant=len(relevant_jobs),
            jobs_above_ats=0,
            applications_prepared=0,
        )
        return

    # 6. Stage 4: JD Analysis
    logger.info("--- Stage 4: Job Description Analysis ---")
    jd_analyzer = JDAnalysisAgent(llm_client)
    analyzed_jobs = jd_analyzer.execute(relevant_jobs)

    # 7. Stage 5: ATS Scoring
    logger.info("--- Stage 5: ATS Scoring ---")
    ats_scorer = ATSScoringAgent()
    scored_jobs = ats_scorer.execute(analyzed_jobs)

    # Write target Indian AI company jobs with computed ATS scores
    if not is_dry_run and sheets_client:
        try:
            target_indian_companies = ["quantiphi", "fractal", "tiger analytics", "tredence", "latentview", "mu sigma", "musigma", "nielseniq", "nielsen", "course5", "gramener", "exl"]
            indian_ai_jobs = []
            for job in scored_jobs:
                comp_name = job.get("company", "").lower()
                if any(tic in comp_name for tic in target_indian_companies):
                    indian_ai_jobs.append({
                        "Company": job.get("company", ""),
                        "Role": job.get("title", ""),
                        "Location": job.get("location", ""),
                        "Experience": job.get("experience", ""),
                        "Job Score": job.get("job_score", 0.0),
                        "ATS Score": job.get("ats_score", 0.0),
                        "Posted Date": job.get("posted_date", ""),
                        "Apply URL": job.get("url", ""),
                        "Status": job.get("status", "new")
                    })
            if indian_ai_jobs:
                logger.info(f"Writing {len(indian_ai_jobs)} target Indian AI company jobs to AnalyticsCompanies sheet")
                sheets_client.add_analytics_company_jobs(indian_ai_jobs)
        except Exception as e:
            logger.error(f"Failed to write target Indian AI company jobs to Google Sheets: {e}")

    # Filter jobs above ATS threshold
    jobs_to_apply = []
    above_ats_count = 0
    for job in scored_jobs:
        if job.get("ats_score", 0) >= settings.min_ats_score:
            above_ats_count += 1
            jobs_to_apply.append(job)
            logger.info(
                f"Accepted:\n"
                f"Title: {job.get('title')}\n"
                f"Company: {job.get('company')}\n"
                f"Role Category: {job.get('role_category')}\n"
                f"Job Score: {job.get('job_score')}\n"
                f"ATS Score: {job.get('ats_score')}"
            )
        else:
            logger.info(
                f"Rejected:\n"
                f"Title: {job.get('title')}\n"
                f"Company: {job.get('company')}\n"
                f"Reason: ATS"
            )

    # Limit to max daily applications
    jobs_to_apply = jobs_to_apply[:settings.max_daily_applications]
    logger.info(f"Preparing application packages for {len(jobs_to_apply)} jobs (above threshold: {above_ats_count}).")

    # 8. Stage 6: Tailored Asset Generation & Outreach
    resume_generator = ResumeGenerator()
    resume_tailorer = ResumeAgent(llm_client)
    cl_agent = CoverLetterAgent(llm_client)
    interview_agent = InterviewAgent(llm_client)
    recruiter_agent = RecruiterAgent(llm_client)
    prepared_count = 0

    for job in jobs_to_apply:
        logger.info(
            f"--- Preparing application package for {job.get('company')} — {job.get('title')} "
            f"(ATS Score: {job.get('ats_score')}) ---"
        )
        try:
            # 1. Tailor Resume Content
            tailored_resume = resume_tailorer.execute(job)
            
            # 2. Compile to PDF
            safe_company = "".join(c for c in job.get('company', 'Unknown') if c.isalnum() or c == "_").replace(" ", "_")
            safe_title = "".join(c for c in job.get('title', 'Unknown') if c.isalnum() or c == "_").replace(" ", "_")
            resume_filename = f"yash_pal_resume_{safe_company}_{safe_title}.pdf"
            resume_path = resume_generator.generate_pdf(tailored_resume, resume_filename)
            
            # 3. Generate Cover Letter
            cl_paths = cl_agent.execute(job, tailored_resume)

            # 4. Generate Interview Prep Guide
            prep_path = interview_agent.execute(job)

            # 5. Generate Recruiter Outreach templates
            outreach = recruiter_agent.execute(job)
            
            prepared_count += 1
            
            # Send Telegram Job Alert Card
            notifier.send_job_card(job)
            
            # 6. Save application record and update status in Sheets
            if not is_dry_run and sheets_client:
                app_record = {
                    "job_id": job.get("job_id"),
                    "company": job.get("company"),
                    "title": job.get("title"),
                    "url": job.get("url"),
                    "ats_score": job.get("ats_score"),
                    "resume_path": str(resume_path),
                    "cover_letter_path": cl_paths.get("pdf_path"),
                    "applied_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S"),
                    "status": "prepared",
                }
                sheets_client.add_application(app_record)
                sheets_client.update_job_status(job.get("job_id"), "prepared")

                # If interview prep sheet was generated, also log the initial tracking record
                if prep_path:
                    sheets_client.add_interview({
                        "job_id": job.get("job_id"),
                        "company": job.get("company"),
                        "role": job.get("title"),
                        "stage": "Applied / Outreach Template Ready",
                        "scheduled_date": "N/A",
                        "prep_path": str(prep_path),
                        "result": "Pending",
                        "notes": f"LinkedIn connection text: {outreach.get('linkedin_template', '')[:100]}...",
                    })
                
        except Exception as e:
            logger.error(f"Failed to prepare application package for {job.get('company')}: {e}", exc_info=True)

    # 9. Stage 7: Skill Gap Analytics
    logger.info("--- Stage 7: Skill Gap Analytics ---")
    skill_gap_agent = SkillGapAgent(sheets_client=sheets_client)
    skill_gap_agent.execute(scored_jobs)

    # Send Daily summary via Telegram
    notifier.send_daily_summary(
        jobs_scraped=len(scraped_jobs),
        jobs_new=len(unique_jobs),
        jobs_relevant=len(relevant_jobs),
        jobs_above_ats=above_ats_count,
        applications_prepared=prepared_count,
    )

    # Update Daily Summary in Sheets
    if not is_dry_run and sheets_client:
        try:
            sheets_client.add_daily_summary(
                jobs_scraped=len(scraped_jobs),
                jobs_new=len(unique_jobs),
                jobs_relevant=len(relevant_jobs),
                jobs_above_ats=above_ats_count,
                applications_prepared=prepared_count,
                skipped=(len(unique_jobs) - len(relevant_jobs)) + (len(relevant_jobs) - prepared_count),
            )
        except Exception as e:
            logger.error(f"Failed to log daily summary: {e}")

    logger.info(f"Pipeline execution completed successfully. Prepared {prepared_count} application packages.")


if __name__ == "__main__":
    args = parse_args()
    setup_logging(level=args.log_level)
    try:
        run_pipeline(mode=args.mode)
    except Exception as exc:
        logger.critical(f"Pipeline crashed: {exc}", exc_info=True)
        # Try to alert user on Telegram of crash
        try:
            TelegramNotifier().send_error_alert(f"Pipeline crashed with exception: {exc}")
        except Exception:
            pass
        sys.exit(1)
