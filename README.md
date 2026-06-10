# AI Job Hunter Agent v3.0 (100% Free Edition)

An automated, AI-powered pipeline that scrapes job postings from target Applicant Tracking Systems (ATS) and job boards daily, filters them against a candidate profile, scores relevance, tailors resumes/cover letters, discover recruiters, generates interview prep materials, logs applications to Google Sheets, and alerts the candidate via Telegram.

Built specifically for **Yash Pal** (B.E. Computer Science in AI & ML, University of Mumbai) targeting AI/ML, GenAI, and Mobile Development roles.

---

## System Architecture

The project is designed as a modular pipeline of independent agents managed by `main.py`:

```
                           [Scrapers] (Greenhouse, Lever, Ashby, SmartRecruiters, Indeed, Workday)
                                │
                                ▼
                       [Aggregated Listings]
                                │
                                ▼
                         [Deduplication] (Filters already stored / applied jobs)
                                │
                                ▼
                         [Relevance Check] (Fuzzy matches titles, experience, location)
                                │
                                ▼
                        [JD Analysis] (Gemini extracts required skills, ATS keywords)
                                │
                                ▼
                          [ATS Scoring] (40% keyword overlap, 60% semantic similarity)
                                │
                                ▼
                         [Score Filter] (Only proceed if ATS score >= 80)
                                │
                                ▼
               ┌────────────────┴────────────────┬────────────────┐
               ▼                                 ▼                ▼
       [Resume Tailoring]                 [Cover Letter]   [Recruiter Outreach]
      (Emphasizes tech stack)              (TXT & PDF)    (LinkedIn connection txt)
               │
               ▼
      [Resume Generator] (WeasyPrint A4 PDF)
```

---

## Directory Layout

- `agents/`: Independent pipeline agents (`scraper`, `dedup`, `relevance`, `jd_analysis`, `ats_scoring`, `resume`, `cover_letter`, `interview_prep`, `recruiter_outreach`, `skill_gap`).
- `scrapers/`: Platform-specific job scrapers.
- `config/`: Application settings, search target profile, and company lists.
- `sheets/`: Client library wrapper for Google Sheets.
- `utils/`: Structured logging, LLM client interface, and rate limiting.
- `knowledge/`: Databases for candidate projects, skills, certifications, and achievements.
- `resume/`: Jinja2 resume templates, stylesheets, and compiled PDFs.
- `reports/`: Generated cover letters and interview prep guides.

---

## Local Setup Instructions

### 1. Prerequisites

You must install system dependencies for **WeasyPrint** (which compiles HTML to PDF) and **Playwright** (for browser scraping):

#### macOS (using Homebrew)
```bash
brew install pango
```

#### Ubuntu / Debian
```bash
sudo apt-get update
sudo apt-get install -y shared-mime-info libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libglib2.0-0 libffi-dev
```

### 2. Install Python Dependencies

Create a virtual environment and install the pinned packages:

```bash
# Using standard python
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Or using uv (much faster)
uv venv
uv pip install -r requirements.txt
```

### 3. Setup Credentials

Copy `.env.example` to `.env` and fill in the variables:

```bash
cp .env.example .env
```

- **`GEMINI_API_KEY`**: Obtain from [Google AI Studio](https://aistudio.google.com/) (free tier).
- **`GOOGLE_SHEETS_CRED_PATH`**: Create a Service Account in [Google Cloud Console](https://console.cloud.google.com/), download the JSON credentials key, and save it in `credentials/service_account.json`.
- **`GOOGLE_SHEET_ID`**: Create a new Google Sheet, share it with the service account email, and copy the sheet ID from the URL.
- **`TELEGRAM_BOT_TOKEN`** & **`TELEGRAM_CHAT_ID`**: Create a bot via `@BotFather` on Telegram and copy the credentials. Get your chat ID using `@userinfobot`.

---

## How to Run

### Run Pipeline
```bash
# Run in Dry-Run Mode (does not write to Sheets, logs matches)
python main.py --mode=dry-run

# Run full daily hunt (prepares applications, writes to Sheets, notifies Telegram)
python main.py --mode=daily

# Scrape only (terminates after Stage 1)
python main.py --mode=scrape-only
```

### Run Interactive Telegram Bot (Optional)
Run the bot listener process in the background:
```bash
python -m telegram_bot.bot
```
Use `/summary`, `/jobs`, or `/status` inside your Telegram chat to interact with your job agent!

### Run in Docker
```bash
docker build -t job-hunter .
docker run --env-file .env job-hunter --mode=daily
```

---

## Customizing Targets

- **Edit Profile**: Open [config/profile.py](file:///Users/yashpal/Documents/Vibe_Project/JOB_HUNT/config/profile.py) to edit degree title, target roles, preferred locations, and excluded keywords.
- **Edit Companies**: Open [config/companies.py](file:///Users/yashpal/Documents/Vibe_Project/JOB_HUNT/config/companies.py) to add board IDs or search queries.
- **Edit Resume Info**: Update files under the [knowledge/](file:///Users/yashpal/Documents/Vibe_Project/JOB_HUNT/knowledge/) folder to add new projects, skills, or certifications.

---

## Deployment (GitHub Actions)

The workflow [.github/workflows/daily_hunt.yml](file:///Users/yashpal/Documents/Vibe_Project/JOB_HUNT/.github/workflows/daily_hunt.yml) is configured to run daily on a cron job.

1. Push this code to a GitHub repository (private or public).
2. Set the following Secrets in the repository (Settings -> Secrets and variables -> Actions):
   - `GEMINI_API_KEY`
   - `GOOGLE_SHEET_ID`
   - `GOOGLE_SHEETS_CREDS` (Paste the entire contents of your Google Service Account JSON key)
   - `TELEGRAM_BOT_TOKEN`
   - `TELEGRAM_CHAT_ID`
3. Download generated resume PDFs and cover letters directly from the GitHub Actions run artifacts!
