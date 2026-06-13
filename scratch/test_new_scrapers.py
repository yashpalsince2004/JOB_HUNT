"""Scratch test script for new Indian AI company scrapers and relevance scoring."""

import sys
from pathlib import Path

# Add project root to python path
project_root = str(Path(__file__).resolve().parent.parent)
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from scrapers.quantiphi_scraper import QuantiphiScraper
from scrapers.fractal_scraper import FractalScraper
from scrapers.tiger_scraper import TigerScraper
from scrapers.tredence_scraper import TredenceScraper
from scrapers.latentview_scraper import LatentviewScraper
from agents.relevance_agent import RelevanceAgent
from telegram_bot.notifier import TelegramNotifier


def test_scrapers_and_scoring():
    print("--- Starting Career Portal Scraper Integration Test ---")
    
    # 1. Instantiate scrapers
    scrapers = [
        QuantiphiScraper(),
        FractalScraper(),
        TigerScraper(),
        TredenceScraper(),
        LatentviewScraper()
    ]
    
    all_jobs = []
    
    # Run scrapers (limit to max 3 jobs per scraper to be fast and polite)
    for scraper in scrapers:
        print(f"\nRunning scraper: {scraper.source_name}...")
        scraper._max_jobs_limit = 3
        try:
            jobs = scraper.scrape()
            print(f"Scraper {scraper.source_name} found {len(jobs)} jobs.")
            for idx, j in enumerate(jobs, 1):
                print(f"  {idx}. {j.company} - {j.title} ({j.location})")
            all_jobs.extend(jobs)
        except Exception as e:
            print(f"Scraper {scraper.source_name} failed: {e}")
            
    print(f"\nTotal scraped jobs: {len(all_jobs)}")
    
    # 2. Score jobs using RelevanceAgent
    print("\n--- Running Relevance Agent ---")
    agent = RelevanceAgent()
    relevant_jobs = agent.run(all_jobs)
    
    print(f"\nRelevant jobs found: {len(relevant_jobs)}")
    for idx, j in enumerate(relevant_jobs, 1):
        print(f"  {idx}. {j.company} - {j.title} ({j.location}) -> Score: {j.job_score} (Priority: {j.company_priority})")
        if j.job_score >= 85:
            print("     🚀 [High Priority Alert Triggered]")
            
    # 3. Test Telegram Alert Format
    print("\n--- Testing Telegram Alert Card Formatting ---")
    notifier = TelegramNotifier()
    if relevant_jobs:
        job = relevant_jobs[0]
        print("Formatting job alert for first match:")
        notifier.send_high_priority_alert(job.to_dict())
    else:
        # Create a mock job to test formatting
        mock_job = {
            "company": "Quantiphi",
            "title": "Applied AI Engineer",
            "location": "Mumbai",
            "job_score": 92.5,
            "url": "https://quantiphi.myworkdayjobs.com/Careers/job/Mumbai/Applied-AI-Engineer_R100"
        }
        print("Formatting mock job alert:")
        notifier.send_high_priority_alert(mock_job)
        
    print("\n--- Test Completed Successfully ---")


if __name__ == "__main__":
    test_scrapers_and_scoring()
