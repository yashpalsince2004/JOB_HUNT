"""
Yash Pal's target job profile configuration.

This module defines what roles, skills, locations, and experience levels
the relevance agent should filter for. Edit this to change targeting.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class TargetProfile:
    """Defines the ideal job search parameters for Yash Pal."""

    name: str = "Yash Pal"
    degree: str = "B.E. Computer Science (AI & ML)"
    university: str = "University of Mumbai"

    # ─── Target Roles (case-insensitive matching) ───
    target_roles: tuple[str, ...] = (
        "ai engineer",
        "artificial intelligence engineer",
        "machine learning engineer",
        "ml engineer",
        "generative ai engineer",
        "genai engineer",
        "llm engineer",
        "ai developer",
        "ai application developer",
        "ai/ml engineer",
        "deep learning engineer",
        "nlp engineer",
        "computer vision engineer",
        "data scientist",
        "ml ops engineer",
        "mlops engineer",
        "flutter developer",
        "android developer",
        "mobile developer",
        "software engineer ai",
        "software engineer ml",
        "software engineer machine learning",
        "software developer ai",
        "full stack ai developer",
        "applied scientist",
        "research engineer",
    )

    # ─── Experience Levels (accept these) ───
    accepted_experience: tuple[str, ...] = (
        "fresher",
        "entry level",
        "entry-level",
        "junior",
        "0-1 years",
        "0-2 years",
        "0-3 years",
        "1-2 years",
        "1-3 years",
        "0 years",
        "1 year",
        "2 years",
        "new grad",
        "graduate",
        "associate",
    )

    # ─── Maximum Years of Experience to Accept ───
    max_experience_years: int = 3

    # ─── Preferred Locations ───
    preferred_locations: tuple[str, ...] = (
        "remote",
        "work from home",
        "wfh",
        "hybrid",
        "mumbai",
        "navi mumbai",
        "thane",
        "pune",
        "bangalore",
        "bengaluru",
        "hyderabad",
        "india",
        "anywhere",
    )

    # ─── Core Skills (for resume matching) ───
    core_skills: tuple[str, ...] = (
        "python",
        "pytorch",
        "tensorflow",
        "keras",
        "scikit-learn",
        "langchain",
        "llm",
        "large language models",
        "generative ai",
        "transformers",
        "hugging face",
        "nlp",
        "natural language processing",
        "computer vision",
        "opencv",
        "deep learning",
        "machine learning",
        "neural networks",
        "rag",
        "retrieval augmented generation",
        "vector databases",
        "chromadb",
        "pinecone",
        "fine-tuning",
        "prompt engineering",
        "flutter",
        "dart",
        "android",
        "kotlin",
        "java",
        "firebase",
        "fastapi",
        "flask",
        "docker",
        "git",
        "sql",
        "mongodb",
        "api",
        "rest api",
    )

    # ─── Title Exclusion Keywords (reject if title contains these) ───
    excluded_title_keywords: tuple[str, ...] = (
        "senior",
        "sr.",
        "sr ",
        "lead",
        "principal",
        "staff",
        "manager",
        "director",
        "vp ",
        "vice president",
        "head of",
        "chief",
        "architect",  # usually 5+ years
        "sales",
        "marketing",
        "recruiter",
        "hr ",
        "human resource",
        "intern",  # usually unpaid / college-only
        "trainee",
    )

    # ─── Companies to Prioritize ───
    priority_companies: tuple[str, ...] = (
        "google",
        "microsoft",
        "meta",
        "amazon",
        "apple",
        "nvidia",
        "openai",
        "anthropic",
        "deepmind",
        "ibm",
        "accenture",
        "capgemini",
        "tcs",
        "infosys",
        "wipro",
        "cognizant",
        "tech mahindra",
        "deloitte",
        "ey",
        "kpmg",
        "pwc",
        "stripe",
        "razorpay",
        "zerodha",
        "flipkart",
        "meesho",
        "swiggy",
        "zomato",
        "cred",
        "phonepe",
    )


# Singleton instance used across the application
PROFILE = TargetProfile()
