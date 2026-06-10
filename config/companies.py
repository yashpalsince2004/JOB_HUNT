"""
Target companies and their ATS platform configurations.

Maps each company to its Applicant Tracking System (ATS) and the
identifiers needed to hit their public job board API.

To add a new company:
  1. Visit their careers page
  2. Open browser DevTools → Network tab
  3. Look for JSON requests to greenhouse.io, lever.co, ashbyhq.com, etc.
  4. Extract the board_id / company slug from the URL
  5. Add an entry below
"""

from dataclasses import dataclass


@dataclass
class CompanyConfig:
    """Configuration for a single company's career page."""

    name: str
    platform: str  # "greenhouse", "lever", "ashby", "smartrecruiters", "workday", "custom"
    board_id: str = ""  # Platform-specific identifier
    careers_url: str = ""  # Direct careers page URL (for custom/workday)
    search_keywords: tuple[str, ...] = ()  # Optional: filter keywords on the platform


# ─── Greenhouse Companies ───
# API: https://api.greenhouse.io/v1/boards/{board_id}/jobs?content=true
GREENHOUSE_COMPANIES = [
    CompanyConfig(name="Stripe", platform="greenhouse", board_id="stripe"),
    CompanyConfig(name="Airbnb", platform="greenhouse", board_id="airbnb"),
    CompanyConfig(name="Cloudflare", platform="greenhouse", board_id="cloudflare"),
    CompanyConfig(name="DoorDash", platform="greenhouse", board_id="doordash"),
    CompanyConfig(name="Notion", platform="greenhouse", board_id="notion"),
    CompanyConfig(name="Discord", platform="greenhouse", board_id="discord"),
    CompanyConfig(name="Figma", platform="greenhouse", board_id="figma"),
    CompanyConfig(name="HashiCorp", platform="greenhouse", board_id="hashicorp"),
    CompanyConfig(name="Databricks", platform="greenhouse", board_id="databricks"),
    CompanyConfig(name="Scale AI", platform="greenhouse", board_id="scaleai"),
    CompanyConfig(name="Cohere", platform="greenhouse", board_id="cohere"),
    CompanyConfig(name="Hugging Face", platform="greenhouse", board_id="huggingface"),
    CompanyConfig(name="Weights & Biases", platform="greenhouse", board_id="wandb"),
    CompanyConfig(name="Anyscale", platform="greenhouse", board_id="anyscale"),
    CompanyConfig(name="Runway", platform="greenhouse", board_id="runwayml"),
    CompanyConfig(name="Stability AI", platform="greenhouse", board_id="stabilityai"),
    CompanyConfig(name="Vercel", platform="greenhouse", board_id="vercel"),
    CompanyConfig(name="Supabase", platform="greenhouse", board_id="supabase"),
    CompanyConfig(name="Replit", platform="greenhouse", board_id="replit"),
]

# ─── Lever Companies ───
# API: https://api.lever.co/v0/postings/{board_id}?mode=json
LEVER_COMPANIES = [
    CompanyConfig(name="Netflix", platform="lever", board_id="netflix"),
    CompanyConfig(name="Spotify", platform="lever", board_id="spotify"),
    CompanyConfig(name="Shopify", platform="lever", board_id="shopify"),
    CompanyConfig(name="Twitch", platform="lever", board_id="twitch"),
    CompanyConfig(name="Confluent", platform="lever", board_id="confluent"),
    CompanyConfig(name="Rippling", platform="lever", board_id="rippling"),
    CompanyConfig(name="Verkada", platform="lever", board_id="verkada"),
    CompanyConfig(name="Coda", platform="lever", board_id="coda"),
    CompanyConfig(name="Dbt Labs", platform="lever", board_id="daboratoies"),
    CompanyConfig(name="Weights & Biases", platform="lever", board_id="wandb"),
]

# ─── Ashby Companies ───
# API: https://api.ashbyhq.com/posting-api/job-board/{board_id}
ASHBY_COMPANIES = [
    CompanyConfig(name="Ramp", platform="ashby", board_id="ramp"),
    CompanyConfig(name="Linear", platform="ashby", board_id="linear"),
    CompanyConfig(name="Cursor", platform="ashby", board_id="cursor"),
    CompanyConfig(name="Perplexity", platform="ashby", board_id="perplexity"),
    CompanyConfig(name="ElevenLabs", platform="ashby", board_id="elevenlabs"),
    CompanyConfig(name="Together AI", platform="ashby", board_id="togetherai"),
    CompanyConfig(name="Mistral AI", platform="ashby", board_id="mistralai"),
]

# ─── SmartRecruiters Companies ───
# API: https://api.smartrecruiters.com/v1/companies/{company_id}/postings
SMARTRECRUITERS_COMPANIES = [
    CompanyConfig(name="Visa", platform="smartrecruiters", board_id="Visa"),
    CompanyConfig(name="KPMG", platform="smartrecruiters", board_id="KPMG"),
    CompanyConfig(name="Bosch", platform="smartrecruiters", board_id="BoschGroup"),
]

# ─── Workday Companies (MNCs) ───
# These require browser-based scraping of Workday career sites
WORKDAY_COMPANIES = [
    CompanyConfig(
        name="Accenture",
        platform="workday",
        careers_url="https://www.accenture.com/in-en/careers/jobsearch",
        search_keywords=("AI", "Machine Learning", "GenAI"),
    ),
    CompanyConfig(
        name="Deloitte",
        platform="workday",
        careers_url="https://apply.deloitte.com/careers",
        search_keywords=("AI", "ML", "Data Science"),
    ),
    CompanyConfig(
        name="EY",
        platform="workday",
        careers_url="https://eygbl.referrals.selectminds.com/",
        search_keywords=("Artificial Intelligence", "Machine Learning"),
    ),
    CompanyConfig(
        name="PwC",
        platform="workday",
        careers_url="https://www.pwc.in/careers.html",
        search_keywords=("AI", "Machine Learning"),
    ),
]

# ─── Custom / Direct Career Pages ───
CUSTOM_COMPANIES = [
    CompanyConfig(
        name="TCS",
        platform="custom",
        careers_url="https://ibegin.tcs.com/iBegin/jobs/search",
        search_keywords=("AI", "ML", "Artificial Intelligence"),
    ),
    CompanyConfig(
        name="Infosys",
        platform="custom",
        careers_url="https://career.infosys.com/joblist",
        search_keywords=("AI", "Machine Learning", "GenAI"),
    ),
    CompanyConfig(
        name="Wipro",
        platform="custom",
        careers_url="https://careers.wipro.com/search-jobs",
        search_keywords=("AI", "ML"),
    ),
    CompanyConfig(
        name="Cognizant",
        platform="custom",
        careers_url="https://careers.cognizant.com/global/en/search-results",
        search_keywords=("AI", "Machine Learning"),
    ),
    CompanyConfig(
        name="Tech Mahindra",
        platform="custom",
        careers_url="https://careers.techmahindra.com/",
        search_keywords=("AI", "ML"),
    ),
    CompanyConfig(
        name="Capgemini",
        platform="custom",
        careers_url="https://www.capgemini.com/in-en/careers/job-search/",
        search_keywords=("AI", "Machine Learning"),
    ),
    CompanyConfig(
        name="IBM",
        platform="custom",
        careers_url="https://www.ibm.com/careers/search",
        search_keywords=("AI", "Machine Learning", "Watson"),
    ),
]

# ─── Indeed Search Queries ───
INDEED_SEARCH_QUERIES = [
    "AI engineer fresher India",
    "machine learning engineer entry level India",
    "generative AI developer India",
    "LLM engineer India",
    "AI ML engineer 0-2 years India",
    "flutter developer fresher India",
    "android developer AI India",
    "NLP engineer entry level India remote",
    "deep learning engineer junior India",
    "computer vision engineer fresher India",
]


def get_all_companies() -> list[CompanyConfig]:
    """Return all configured companies across all platforms."""
    return (
        GREENHOUSE_COMPANIES
        + LEVER_COMPANIES
        + ASHBY_COMPANIES
        + SMARTRECRUITERS_COMPANIES
        + WORKDAY_COMPANIES
        + CUSTOM_COMPANIES
    )


def get_companies_by_platform(platform: str) -> list[CompanyConfig]:
    """Filter companies by their ATS platform."""
    return [c for c in get_all_companies() if c.platform == platform]
