"""
Relevance Agent.

Filters job listings to ensure they match Yash Pal's profile.
Uses a hybrid scoring system (0-100) based on title, skills, experience, and location.
Accepts jobs with a total score >= 60.
Logs detailed matched/rejection diagnostics.
"""

import re
from typing import Any

from agents.base_agent import BaseAgent
from config.profile import PROFILE, TargetProfile
from scrapers.base_scraper import JobListing


class RelevanceAgent(BaseAgent):
    """Filters jobs using a 6-component 0-100 scoring system matching Yash's target profile."""

    # Title patterns for taxonomy classification
    TITLE_PATTERNS = {
        "GENAI_ENGINEERING": [r"\bgenai\b", r"\bgenerative\s+ai\b", r"\bllm\b", r"\bprompt\b", r"\bgpt\b", r"\bclaude\b", r"\bcopilot\b", r"\brag\b"],
        "NLP": [r"\bnlp\b", r"\bnatural\s+language\b"],
        "COMPUTER_VISION": [r"\bcomputer\s+vision\b", r"\bcv\b", r"\bimage\s+processing\b", r"\bobject\s+detection\b"],
        "ML_ENGINEERING": [r"\bml\b", r"\bmachine\s+learning\b", r"\bdeep\s+learning\b", r"\bml\s+engineer\b", r"\bml\s+developer\b", r"\bmachine\s+learning\s+specialist\b", r"\bmachine\s+learning\s+software\b"],
        "AI_ENGINEERING": [r"\bai\b", r"\bartificial\s+intelligence\b", r"\bai\s+engineer\b", r"\bai\s+developer\b", r"\bai\s+application\b", r"\bapplied\s+ai\b"],
        "DATA_SCIENCE": [r"\bdata\s+scientist\b", r"\bdata\s+science\b", r"\bdecision\s+scientist\b"],
        "PYTHON_BACKEND": [r"\bpython\b", r"\bbackend\b", r"\bdjango\b", r"\bflask\b", r"\bfastapi\b"],
        "MOBILE_ANDROID": [r"\bandroid\b"],
        "MOBILE_FLUTTER": [r"\bflutter\b"],
        "PLATFORM_ENGINEERING": [r"\bml\s+platform\b", r"\bai\s+platform\b", r"\bmlops\b", r"\bllmops\b", r"\bplatform\s+engineer\b", r"\binfrastructure\b"],
        "SOFTWARE_ENGINEERING": [r"\bsoftware\b", r"\bdeveloper\b", r"\bengineer\b", r"\bassociate\b", r"\bgraduate\b", r"\bmobile\b", r"\bfull\s+stack\b"],
    }

    # Description keywords for each taxonomy category
    DESC_KEYWORDS = {
        "GENAI_ENGINEERING": ["llm", "generative ai", "genai", "prompt", "langchain", "llamaindex", "transformers", "gpt", "claude", "gemini", "openai", "rag"],
        "NLP": ["nlp", "natural language", "spacy", "nltk", "bert", "huggingface", "tokenization", "text mining"],
        "COMPUTER_VISION": ["computer vision", "opencv", "yolo", "cnn", "image processing", "object detection", "segmentation", "pytorch", "tensorflow"],
        "ML_ENGINEERING": ["pytorch", "tensorflow", "keras", "scikit-learn", "machine learning", "mlops", "model training", "deep learning", "neural networks"],
        "AI_ENGINEERING": ["artificial intelligence", "ai engineer", "ai developer", "applied ai", "neural networks", "agent", "cognitive"],
        "DATA_SCIENCE": ["data science", "pandas", "numpy", "scikit-learn", "jupyter", "statistics", "statistical", "analytics", "sql", "modeling"],
        "PYTHON_BACKEND": ["python", "fastapi", "flask", "django", "backend", "rest api", "sql", "postgresql", "graphene", "graphql"],
        "MOBILE_ANDROID": ["android", "kotlin", "java", "gradle", "mobile"],
        "MOBILE_FLUTTER": ["flutter", "dart", "mobile", "cross-platform"],
        "PLATFORM_ENGINEERING": ["kubernetes", "docker", "aws", "gcp", "mlops", "ci/cd", "terraform", "infrastructure", "devops", "pipelines"],
        "SOFTWARE_ENGINEERING": ["software development", "programming", "git", "sql", "rest", "architecture", "agile", "computer science"],
    }

    # Precedence order of categories for classification ties
    PRECEDENCE = [
        "GENAI_ENGINEERING", "NLP", "COMPUTER_VISION", "ML_ENGINEERING",
        "AI_ENGINEERING", "PLATFORM_ENGINEERING", "MOBILE_FLUTTER",
        "MOBILE_ANDROID", "PYTHON_BACKEND", "DATA_SCIENCE", "SOFTWARE_ENGINEERING"
    ]

    @property
    def name(self) -> str:
        return "relevance"

    def __init__(self, profile: TargetProfile = PROFILE) -> None:
        super().__init__()
        self._profile = profile

    def _get_words(self, text: str) -> set[str]:
        """Helper to tokenize text into a set of lowercased words."""
        cleaned = re.sub(r"[^\w\s\+]", " ", text.lower())
        return {w for w in cleaned.split() if w}

    def _calculate_title_score(self, title: str) -> tuple[int, str]:
        """
        Calculate title match score (max 40 points).
        Maintained for backwards-compatibility with existing tests.
        """
        title_lower = title.lower()
        title_words = self._get_words(title)

        # 1. Exact phrase match first
        for role in self._profile.target_roles:
            if role in title_lower:
                return 40, f"Exact match for target role: '{role}'"

        # 2. Token overlap ratio match
        max_overlap = 0.0
        best_role = ""
        for role in self._profile.target_roles:
            role_words = self._get_words(role)
            if not role_words:
                continue
            intersection = title_words & role_words
            overlap = len(intersection) / len(role_words)
            if overlap > max_overlap:
                max_overlap = overlap
                best_role = role

        if max_overlap > 0:
            score = int(max_overlap * 40)
            return score, f"Fuzzy match with target role '{best_role}' (overlap: {max_overlap:.2f})"

        # 3. Fallback: check fuzzy keywords
        fuzzy_keywords = [
            "ai", "ml", "nlp", "flutter", "android", "machine learning",
            "deep learning", "cv", "python", "backend", "software",
            "developer", "engineer", "mobile", "ios"
        ]
        matched_kws = [kw for kw in fuzzy_keywords if kw in title_lower or any(w == kw for w in title_words)]
        if matched_kws:
            return 20, f"Title matched fuzzy keywords: {matched_kws}"

        return 0, "No title match"

    def _matches_title_phrases(self, title: str) -> bool:
        """Check if the title matches any of the target roles or custom phrases."""
        title_lower = title.lower()
        accepted_phrases = list(self._profile.target_roles) + [
            "decision scientist", "analytics consultant", "machine learning specialist",
            "machine learning software engineer", "ml platform engineer", "ai platform engineer",
            "ai software engineer", "graduate ml engineer", "junior ai developer",
            "associate ai engineer", "ai research engineer", "prompt engineer", "genai developer"
        ]
        normalized_title = title_lower.replace("/", " ")
        for phrase in accepted_phrases:
            if phrase in normalized_title:
                return True
        return False

    def _check_title_exclusions(self, title: str, exp_years: float | None) -> tuple[bool, str]:
        """
        Check if title contains any of the excluded keywords.
        Exclusions for senior roles are skipped if required experience is <= 3 years.
        Non-tech role exclusions are checked unconditionally.
        """
        title_lower = title.lower()

        # 1. Unconditional non-tech exclusions
        non_tech_keywords = [
            "hr", "recruiter", "recruiting", "sales", "marketing", "finance", 
            "operations", "support", "customer support", "talent acquisition", 
            "business development", "accountant", "designer", "content writer", 
            "product manager", "project manager", "scrum master"
        ]
        for kw in non_tech_keywords:
            pattern = rf"\b{re.escape(kw)}\b"
            if re.search(pattern, title_lower):
                return False, f"Title contains non-tech excluded keyword '{kw}'"

        # 2. Conditional senior/lead exclusions
        senior_keywords = [
            "senior", "lead", "principal", "staff", "director", "manager", "vp", "chief", "sr.", "sr ", "architect", "head of"
        ]
        has_senior_kw = False
        matched_kw = ""
        for kw in senior_keywords:
            pattern = rf"\b{re.escape(kw)}\b" if kw not in ["sr.", "sr "] else re.escape(kw)
            if re.search(pattern, title_lower):
                has_senior_kw = True
                matched_kw = kw.strip()
                break

        if has_senior_kw:
            if exp_years is not None and 0.0 <= exp_years <= 3.0:
                # Accept if experience is explicitly low (<= 3 years)
                return True, ""
            else:
                return False, f"Title contains excluded keyword '{matched_kw}' and experience is > 3 years or unknown"

        return True, ""

    def _matches_title(self, title: str) -> bool:
        """Compatibility wrapper for unit tests checking if a title matches."""
        is_valid, _ = self._check_title_exclusions(title, None)
        if not is_valid:
            return False
        
        # To maintain backwards compatibility, check if it matches target title phrases
        # or has a valid classified role category.
        if self._matches_title_phrases(title):
            return True
            
        classification = self.classify_role(title, "")
        return classification["category"] != "OTHER"

    def _evaluate_location(self, location: str) -> tuple[bool, float, str]:
        """
        Evaluate if location is acceptable and compute priority score (0-100).
        Returns (is_accepted, location_priority_score, reason).
        """
        if not location:
            # Default match for unspecified location
            return True, 70.0, "Location not specified"

        loc_lower = location.lower()

        # 1. Determine remote status
        remote_keywords = ["remote", "wfh", "work from home", "anywhere", "worldwide", "global", "telecommute"]
        is_remote = any(kw in loc_lower for kw in remote_keywords)

        # Check for remote location types
        if is_remote:
            is_remote_india = "india" in loc_lower or "in" in re.split(r'\W+', loc_lower)
            is_worldwide = any(kw in loc_lower for kw in ["worldwide", "global", "anywhere", "world-wide"])

            if is_remote_india:
                return True, 90.0, "Remote India"
            elif is_worldwide:
                return True, 85.0, "Worldwide Remote"
            else:
                foreign_indicators = ["us", "usa", "uk", "london", "europe", "canada", "germany", "france", "singapore"]
                if any(fi in loc_lower for fi in foreign_indicators):
                    return True, 85.0, "Worldwide Remote"
                return True, 90.0, "Remote India"

        # 2. Strict onsite location parser & blacklist
        blacklist_regions = [
            "usa", "united states", "us", "san francisco", "new york", "silicon valley", "california",
            "uk", "united kingdom", "london", "germany", "france", "berlin", "paris", "europe",
            "canada", "toronto", "vancouver", "brazil", "mexico", "latam", "latin america", "argentina",
            "singapore", "malaysia", "thailand", "spain", "dubai", "uae"
        ]

        words = re.split(r'\W+', loc_lower)
        for reg in blacklist_regions:
            if reg in words or (len(reg) > 3 and reg in loc_lower):
                return False, 0.0, f"International onsite in {reg}"

        # If not remote and no India location is mentioned, imply international onsite and reject
        india_keywords = [
            "india", "mumbai", "navi mumbai", "thane", "pune", "bangalore", "bengaluru",
            "hyderabad", "chennai", "noida", "gurgaon", "delhi", "ncr", "kolkata", "ahmedabad",
            "jaipur", "gurugram", "karnataka", "maharashtra", "telangana", "tamil nadu", "haryana",
            "coimbatore", "kochi", "kerala", "indore", "chandigarh"
        ]
        is_india = any(kw in loc_lower for kw in india_keywords)
        if not is_india:
            return False, 0.0, "International onsite implied"

        # 3. Score acceptable Indian onsite / hybrid locations
        if "navi mumbai" in loc_lower or "thane" in loc_lower or "mumbai" in loc_lower:
            return True, 100.0, "Mumbai/Navi Mumbai/Thane Region"
            
        if "pune" in loc_lower:
            return True, 95.0, "Pune Region"

        if "bangalore" in loc_lower or "bengaluru" in loc_lower:
            return True, 75.0, "Bangalore"

        if any(w in loc_lower for w in ["hyderabad", "chennai", "noida", "gurgaon", "gurugram"]):
            return True, 70.0, "Hyderabad/Chennai/Noida/Gurgaon"

        return True, 70.0, "Other India location"

    def _matches_location(self, location: str) -> bool:
        """Compatibility wrapper for unit tests checking if a location is allowed."""
        is_valid, _, _ = self._evaluate_location(location)
        return is_valid

    def _extract_experience(self, text: str) -> float | None:
        """
        Extract required years of experience from description or title using regex.
        Returns the minimum required experience found.
        """
        if not text:
            return None

        text_clean = text.replace('\xa0', ' ').lower()

        # 1. Range patterns, e.g. "2-5 years", "2 to 4 years"
        range_pattern = r"\b(\d+(?:\.\d+)?)\s*(?:-|to)\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)\b"
        range_matches = re.findall(range_pattern, text_clean)
        if range_matches:
            try:
                return float(range_matches[0][0])
            except ValueError:
                pass

        # 2. Single value patterns, e.g. "3+ years", "3 years of experience", "minimum 3 years"
        patterns = [
            r"\b(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)\b",
            r"\b(?:experience\s*of\s*|experience:\s*|experience\s*required:\s*)(\d+(?:\.\d+)?)\b",
        ]
        for pat in patterns:
            matches = re.findall(pat, text_clean)
            if matches:
                try:
                    val = float(matches[0])
                    if 0.5 <= val <= 20.0:
                        return val
                except ValueError:
                    pass

        return None

    def _evaluate_experience(self, title: str, description: str) -> tuple[bool, float, str]:
        """
        Evaluate experience constraints and calculate score (max 20 points).
        Returns (is_accepted, score_out_of_20, reason).
        """
        title_lower = title.lower()
        desc_lower = description.lower() if description else ""

        # Check if title or description indicates entry-level
        entry_keywords = ["fresher", "graduate", "associate", "entry level", "entry-level", "junior", "trainee", "intern", "internship"]
        is_entry_title = any(kw in title_lower for kw in entry_keywords)
        is_entry_desc = any(kw in desc_lower for kw in ["fresher", "no experience required", "freshers welcome", "entry level", "entry-level"])
        is_entry_role = is_entry_title or is_entry_desc

        exp_years = self._extract_experience(description)
        if exp_years is None:
            exp_years = self._extract_experience(title)

        if exp_years is not None:
            if exp_years > 3.0:
                if is_entry_role:
                    return True, 20.0, f"Experience {exp_years} yrs > max 3.0 but accepted due to entry-level keywords"
                else:
                    return False, 0.0, f"Experience required ({exp_years} yrs) exceeds max (3.0 yrs)"
            return True, 20.0, f"Experience within range ({exp_years} yrs)"

        return True, 16.0, "Experience not mentioned (default match)"

    def _calculate_skill_score(self, title: str, description: str) -> tuple[int, list[str]]:
        """
        Calculate skill match score (max 30 points).
        Matches against core_skills and scores 6 points per match up to 5 matched skills.
        """
        combined_text = f"{title} {description or ''}".lower()
        matched_skills = []
        for skill in self._profile.core_skills:
            escaped_skill = re.escape(skill)
            pattern = ""
            if re.match(r"^\w", skill):
                pattern += r"\b"
            pattern += escaped_skill
            if re.search(r"\w$", skill):
                pattern += r"\b"

            if re.search(pattern, combined_text):
                matched_skills.append(skill)

        score = min(30, len(matched_skills) * 6)
        return score, matched_skills

    def _has_ml_data_ai_relevance(self, text: str) -> bool:
        """Check if role matches ML, Data or AI work keywords."""
        keywords = [
            "machine learning", "ml", "data science", "ai", "artificial intelligence",
            "llm", "genai", "generative ai", "python", "sql", "predictive", "modeling",
            "statistics", "model", "analytics", "nlp", "computer vision", "pandas",
            "pytorch", "tensorflow", "scikit-learn"
        ]
        text_lower = text.lower()
        return any(kw in text_lower for kw in keywords)

    def _has_platform_relevance(self, text: str) -> bool:
        """Check if role matches ML or AI Platform work keywords."""
        keywords = [
            "ml platform", "ai platform", "machine learning platform", "ai infrastructure",
            "ml infrastructure", "cloud ai", "mlops", "llmops", "kubeflow", "mlflow",
            "kubernetes", "docker", "aws", "gcp", "azure", "ci/cd", "pipelines"
        ]
        text_lower = text.lower()
        return any(kw in text_lower for kw in keywords)

    def classify_role(self, title: str, description: str) -> dict[str, Any]:
        """
        Classifies a job listing into one of 11 categories and calculates confidence.
        """
        title_lower = title.lower()
        desc_lower = description.lower() if description else ""

        # 1. Special custom titles mapping
        if "decision scientist" in title_lower:
            return {"category": "DATA_SCIENCE", "confidence": 95.0, "role_score": 95.0}

        if "analytics consultant" in title_lower:
            if self._has_ml_data_ai_relevance(desc_lower):
                return {"category": "DATA_SCIENCE", "confidence": 90.0, "role_score": 90.0}
            else:
                return {"category": "OTHER", "confidence": 0.0, "role_score": 0.0}

        if "machine learning software platform engineer" in title_lower:
            return {"category": "PLATFORM_ENGINEERING", "confidence": 95.0, "role_score": 95.0}

        if "machine learning specialist" in title_lower or "machine learning software engineer" in title_lower:
            return {"category": "ML_ENGINEERING", "confidence": 95.0, "role_score": 95.0}

        if "ml platform engineer" in title_lower or "ai platform engineer" in title_lower:
            return {"category": "PLATFORM_ENGINEERING", "confidence": 95.0, "role_score": 95.0}

        if "ai software engineer" in title_lower or "junior ai developer" in title_lower or "associate ai engineer" in title_lower or "ai research engineer" in title_lower:
            return {"category": "AI_ENGINEERING", "confidence": 95.0, "role_score": 95.0}

        if "graduate ml engineer" in title_lower:
            return {"category": "ML_ENGINEERING", "confidence": 95.0, "role_score": 95.0}

        if "prompt engineer" in title_lower or "genai developer" in title_lower:
            return {"category": "GENAI_ENGINEERING", "confidence": 95.0, "role_score": 95.0}

        if "devops" in title_lower:
            if self._has_platform_relevance(desc_lower):
                return {"category": "PLATFORM_ENGINEERING", "confidence": 90.0, "role_score": 90.0}
            else:
                return {"category": "OTHER", "confidence": 0.0, "role_score": 0.0}

        # 2. General taxonomy classification based on scores matching patterns
        best_cat = "OTHER"
        best_score = 0.0
        title_matched = False

        for cat in self.PRECEDENCE:
            score = 0.0
            t_match = False
            for pat in self.TITLE_PATTERNS[cat]:
                if re.search(pat, title_lower):
                    t_match = True
                    break

            if t_match:
                score += 70.0

            # Description keyword matches (up to 30 points)
            desc_keywords = self.DESC_KEYWORDS[cat]
            matches = sum(1 for kw in desc_keywords if re.search(r"\b" + re.escape(kw) + r"\b", desc_lower))
            score += min(30.0, matches * 5.0)

            # We use strict inequality to keep the precedence order in case of ties
            if score > best_score:
                best_score = score
                best_cat = cat
                title_matched = t_match

        if best_cat == "OTHER" or best_score < 40.0:
            return {"category": "OTHER", "confidence": 0.0, "role_score": 0.0}

        # Calculate confidence using the original logic
        desc_keywords = self.DESC_KEYWORDS[best_cat]
        desc_matches = sum(1 for kw in desc_keywords if re.search(r"\b" + re.escape(kw) + r"\b", desc_lower))
        
        if title_matched:
            confidence = min(100.0, 90.0 + desc_matches)
        else:
            confidence = min(89.0, 70.0 + desc_matches)

        return {"category": best_cat, "confidence": confidence, "role_score": confidence}

    def _get_company_priority(self, company: str) -> int:
        comp_lower = company.lower().strip()

        # India Company Tiers
        # Tier A (100)
        if "quantiphi" in comp_lower:
            return 100
        if "fractal" in comp_lower:
            return 100

        # Tier B (95)
        if "tiger analytics" in comp_lower or "tiger" in comp_lower:
            return 95
        if "tredence" in comp_lower:
            return 95
        if "latentview" in comp_lower:
            return 95
        if "mu sigma" in comp_lower or "musigma" in comp_lower:
            return 95
        if "nielseniq" in comp_lower or "nielsen" in comp_lower:
            return 95
        if "course5" in comp_lower:
            return 95
        if "gramener" in comp_lower:
            return 95

        # Tier C (90)
        if "exl" in comp_lower:
            return 90

        # Tech Giants & Consultancies Tiers
        tier1 = ["google", "microsoft", "meta", "amazon", "nvidia", "ibm"]
        tier2 = ["accenture", "capgemini", "tcs", "tata consultancy", "infosys", "wipro", "cognizant", "tech mahindra", "deloitte", "ey", "kpmg", "pwc", "ltimindtree", "persistent"]

        for c in tier1:
            if c in comp_lower:
                return 100
        for c in tier2:
            if c in comp_lower:
                return 90

        return 70

    def _calculate_freshness_score(self, posted_date_str: str) -> int:
        """
        Calculate freshness score based on the posted date string.
        Posted Today = 100
        1–3 Days = 90
        4–7 Days = 80
        8–14 Days = 60
        15–30 Days = 40
        30+ Days = 0
        """
        if not posted_date_str:
            return 80  # Default middle score for unknown/missing dates

        date_lower = posted_date_str.lower().strip()

        # Check for absolute today/recent indicators
        today_words = ["today", "just now", "hours ago", "hour ago", "mins ago", "minute ago", "0 days ago", "active: today", "active today"]
        if any(w in date_lower for w in today_words):
            return 100

        # Check for relative day counts
        day_match = re.search(r"(\d+)\s+day", date_lower)
        if day_match:
            try:
                days = int(day_match.group(1))
                if days == 0:
                    return 100
                elif 1 <= days <= 3:
                    return 90
                elif 4 <= days <= 7:
                    return 80
                elif 8 <= days <= 14:
                    return 60
                elif 15 <= days <= 30:
                    return 40
                else:
                    return 0
            except ValueError:
                pass

        # Check for relative week counts
        week_match = re.search(r"(\d+)\s+week", date_lower)
        if week_match:
            try:
                weeks = int(week_match.group(1))
                days = weeks * 7
                if days <= 7:
                    return 80
                elif 8 <= days <= 14:
                    return 60
                elif 15 <= days <= 30:
                    return 40
                else:
                    return 0
            except ValueError:
                pass

        if "month" in date_lower:
            return 0

        # Try to parse standard dates (e.g. YYYY-MM-DD or ISO format)
        try:
            from datetime import datetime, timezone
            clean_date = re.sub(r"\.\d+Z$", "Z", posted_date_str)
            if "t" in clean_date.lower() or "z" in clean_date.lower():
                dt = datetime.fromisoformat(clean_date.replace("Z", "+00:00"))
            else:
                match_ymd = re.match(r"^(\d{4})-(\d{2})-(\d{2})", clean_date)
                if match_ymd:
                    dt = datetime(int(match_ymd.group(1)), int(match_ymd.group(2)), int(match_ymd.group(3)), tzinfo=timezone.utc)
                else:
                    raise ValueError("Not standard YYYY-MM-DD")
            
            now = datetime.now(timezone.utc)
            delta_days = (now - dt).days
            if delta_days <= 0:
                return 100
            elif 1 <= delta_days <= 3:
                return 90
            elif 4 <= delta_days <= 7:
                return 80
            elif 8 <= delta_days <= 14:
                return 60
            elif 15 <= delta_days <= 30:
                return 40
            else:
                return 0
        except Exception:
            pass

        return 80  # Default fallback

    def run(self, listings: list[JobListing]) -> list[JobListing]:
        """
        Filter job listings by scoring suitability.

        Args:
            listings: List of deduplicated JobListing objects.

        Returns:
            Filtered list of relevant JobListing objects (score >= 60).
        """
        relevant_listings: list[JobListing] = []

        for listing in listings:
            title = listing.title
            company = listing.company

            # Extract experience first
            exp_years = self._extract_experience(listing.description)
            if exp_years is None:
                exp_years = self._extract_experience(title)

            # 1. Hard Exclusion: Title keywords (senior/lead check)
            is_valid_title, title_reason = self._check_title_exclusions(title, exp_years)
            if not is_valid_title:
                listing.hard_reject = True
                listing.rejection_reason = f"Title excluded: {title_reason}"
                listing.final_decision = "reject"
                self.logger.info(f"Rejected: {title} at {company} - {title_reason}")
                continue

            # 2. Hard Exclusion: Location
            is_valid_loc, loc_score, loc_reason = self._evaluate_location(listing.location)
            if not is_valid_loc or loc_score == 0:
                listing.hard_reject = True
                listing.location_category = loc_reason
                listing.location_score = loc_score
                listing.rejection_reason = f"Location excluded: {loc_reason}"
                listing.final_decision = "reject"
                self.logger.info(f"Rejected: {title} at {company} - Location: {listing.location} ({loc_reason})")
                continue

            # 3. Role Classification
            classification = self.classify_role(title, listing.description)
            role_category = classification["category"]
            role_score = classification["role_score"]
            role_confidence = classification["confidence"]

            if role_category == "OTHER" or role_score < 40.0:
                listing.hard_reject = True
                listing.role_category = "OTHER"
                listing.role_score = role_score
                listing.role_confidence = role_confidence
                listing.rejection_reason = "Role classification determined irrelevant (OTHER)"
                listing.final_decision = "reject"
                self.logger.info(f"Rejected: {title} at {company} - Role categorized as OTHER")
                continue

            # 4. Experience Range Check
            is_valid_exp, raw_exp_score, exp_reason = self._evaluate_experience(title, listing.description)
            if not is_valid_exp:
                listing.hard_reject = True
                listing.extracted_experience_years = exp_years if exp_years is not None else -1.0
                listing.experience_score = 0.0
                listing.experience_category = "Senior"
                listing.rejection_reason = f"Experience excluded: {exp_reason}"
                listing.final_decision = "reject"
                self.logger.info(f"Rejected: {title} at {company} - Experience: {exp_reason}")
                continue

            # Calculate scores
            raw_skill_score, matched_skills = self._calculate_skill_score(title, listing.description)
            normalized_skill_score = min(100.0, len(matched_skills) * 20.0)

            company_score = self._get_company_priority(company)
            freshness_score = self._calculate_freshness_score(listing.posted_date)
            experience_score = raw_exp_score * 5.0  # Normalize to 100

            # Calculate salary score (LPA)
            salary_lpa = 0.0
            sal_val = listing.salary_max if listing.salary_max > 0 else listing.salary_min
            if sal_val > 0:
                if listing.salary_period == "monthly":
                    annual_sal = sal_val * 12
                else:
                    annual_sal = sal_val
                    
                if listing.salary_currency == "USD":
                    annual_sal *= 80.0
                    
                salary_lpa = annual_sal / 100000.0
                
            salary_score = 0
            if salary_lpa >= 15.0:
                salary_score = 20
            elif salary_lpa >= 10.0:
                salary_score = 15
            elif salary_lpa >= 8.0:
                salary_score = 10
            elif salary_lpa >= 6.0:
                salary_score = 5

            # Calculate Easy Apply bonus
            easy_apply = False
            if listing.source in ["naukri", "foundit", "cutshort", "talentd"]:
                easy_apply = True
            
            easy_apply_bonus = 10 if easy_apply else 0

            # Calculate company bonus
            company_bonus = 0
            comp_lower = company.lower().strip()
            if "quantiphi" in comp_lower:
                company_bonus = 20
            elif "fractal" in comp_lower:
                company_bonus = 20
            elif "tiger analytics" in comp_lower or "tiger" in comp_lower:
                company_bonus = 20
            elif "mu sigma" in comp_lower or "musigma" in comp_lower:
                company_bonus = 15
            elif "course5" in comp_lower:
                company_bonus = 15
            elif "nielseniq" in comp_lower or "nielsen" in comp_lower:
                company_bonus = 15
            elif "exl" in comp_lower:
                company_bonus = 15
            elif "gramener" in comp_lower:
                company_bonus = 15

            # Calculate total weighted job score (0-100)
            base_job_score = (
                0.25 * role_score +
                0.25 * loc_score +
                0.20 * normalized_skill_score +
                0.10 * company_score +
                0.10 * experience_score +
                0.10 * freshness_score
            )
            
            job_score = base_job_score + company_bonus + salary_score + easy_apply_bonus
            job_score = min(100.0, round(job_score, 1))

            # Assign fields to JobListing
            listing.role_category = role_category
            listing.role_confidence = role_confidence
            listing.role_score = role_score
            
            listing.location_category = loc_reason
            listing.location_score = loc_score
            
            listing.extracted_experience_years = exp_years if exp_years is not None else -1.0
            listing.experience_category = "Entry Level" if (exp_years is not None and exp_years <= 1.0) else ("Mid Level" if (exp_years is not None and exp_years <= 3.0) else "Unknown")
            listing.experience_score = experience_score
            
            listing.skill_score = normalized_skill_score
            listing.company_priority = company_score
            listing.freshness_score = freshness_score
            listing.job_score = job_score
            listing.skills = ", ".join(matched_skills)
            listing.easy_apply = easy_apply

            listing.score_breakdown = (
                f"Role: {role_score}*0.25 | "
                f"Loc: {loc_score}*0.25 | "
                f"Skill: {normalized_skill_score}*0.20 | "
                f"Comp: {company_score}*0.10 | "
                f"Exp: {experience_score}*0.10 | "
                f"Fresh: {freshness_score}*0.10 | "
                f"CompBonus: {company_bonus} | "
                f"SalBonus: {salary_score} | "
                f"EasyBonus: {easy_apply_bonus}"
            )

            # Check Job Score Threshold
            if job_score >= 60.0:
                listing.final_decision = "queue_for_llm"
                listing.status = "new"
                relevant_listings.append(listing)
            else:
                listing.final_decision = "reject"
                listing.rejection_reason = f"Job score {job_score} below threshold 60"
                self.logger.info(f"Rejected: {title} at {company} - Score {job_score} < 60")

        self.logger.info(
            f"Relevance filtering finished: {len(listings)} input -> "
            f"{len(relevant_listings)} relevant (filtered {len(listings) - len(relevant_listings)} irrelevant)"
        )
        return relevant_listings
