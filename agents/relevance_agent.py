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
    """Filters jobs using a 0-100 scoring system matching Yash's target profile."""

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
        Checks for exact phrase matches, token overlap, and fuzzy keyword fallbacks.
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
        """Check if the title matches any of the target roles."""
        title_lower = title.lower()
        accepted_phrases = [
            "ai engineer", "applied ai engineer", "ai software engineer", "ai developer",
            "ai application developer", "machine learning engineer", "ml engineer",
            "machine learning developer", "deep learning engineer", "nlp engineer",
            "computer vision engineer", "data scientist", "research engineer", "ai researcher",
            "llm engineer", "generative ai engineer", "genai engineer", "prompt engineer",
            "python developer", "backend developer", "software engineer",
            "associate software engineer", "graduate engineer", "flutter developer",
            "android developer", "mobile developer", "software developer", "ml developer", "ai/ml engineer"
        ]
        # Normalize slashes/punctuation
        normalized_title = title_lower.replace("/", " ")
        for phrase in accepted_phrases:
            if phrase in normalized_title:
                return True
        return False

    def _check_title_exclusions(self, title: str, exp_years: int | None) -> tuple[bool, str]:
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
            "product manager", "project manager"
        ]
        for kw in non_tech_keywords:
            pattern = rf"\b{re.escape(kw)}"
            if re.search(pattern, title_lower):
                return False, f"Title contains non-tech excluded keyword '{kw}'"
        
        # 2. Conditional senior/lead exclusions
        reject_keywords = ["senior", "lead", "principal", "staff", "director", "manager", "vp", "chief", "sr.", "sr "]
        has_reject_kw = False
        matched_kw = ""
        for kw in reject_keywords:
            pattern = rf"\b{re.escape(kw)}"
            if re.search(pattern, title_lower):
                has_reject_kw = True
                matched_kw = kw
                break
                
        if has_reject_kw:
            if exp_years is not None and exp_years <= 3:
                return True, ""
            else:
                return False, f"Title contains excluded keyword '{matched_kw}' and experience is > 3 years or unknown"
                
        return True, ""

    def _matches_title(self, title: str) -> bool:
        """Compatibility wrapper for unit tests checking if a title matches."""
        is_valid, _ = self._check_title_exclusions(title, None)
        if not is_valid:
            return False
        return self._matches_title_phrases(title)

    def _evaluate_location(self, location: str) -> tuple[bool, int, str]:
        """
        Evaluate if location is acceptable and compute priority score (0-100).
        Returns (is_accepted, location_priority_score, reason).
        """
        if not location:
            # Default match for unspecified location
            return True, 75, "Location not specified"

        loc_lower = location.lower()

        # Remote/hybrid keywords check
        is_remote = any(kw in loc_lower for kw in ["remote", "wfh", "work from home", "anywhere", "worldwide", "global"])

        # Strictly onsite international checks (if not remote)
        if not is_remote:
            if any(w in loc_lower for w in ["usa", "united states", "san francisco", "new york", "silicon valley"]):
                return False, 0, "USA Onsite"
            if any(w in loc_lower for w in ["uk", "united kingdom", "london", "germany", "france", "berlin", "paris", "europe"]):
                return False, 0, "Europe Onsite"
            if any(w in loc_lower for w in ["canada", "toronto", "vancouver"]):
                return False, 0, "Canada Onsite"
            if any(w in loc_lower for w in ["brazil", "mexico", "latam", "latin america", "argentina"]):
                return False, 0, "LATAM Onsite"

        # Score acceptable locations:
        if "navi mumbai" in loc_lower or "thane" in loc_lower or "mumbai" in loc_lower:
            return True, 100, "Mumbai/Navi Mumbai/Thane Region"
            
        if "pune" in loc_lower:
            return True, 95, "Pune Region"

        if is_remote:
            if any(w in loc_lower for w in ["us", "usa", "uk", "london", "europe", "worldwide", "global", "anywhere", "canada", "germany", "france"]):
                return True, 85, "Worldwide Remote"
            # Otherwise default to Remote India
            return True, 90, "Remote India"

        if "bangalore" in loc_lower or "bengaluru" in loc_lower:
            return True, 75, "Bangalore"

        if any(w in loc_lower for w in ["hyderabad", "chennai", "noida", "gurgaon"]):
            return True, 70, "Hyderabad/Chennai/Noida/Gurgaon"

        # If it is international onsite, reject (score 0)
        # Check if location contains any Indian tech cities or "india"
        if not any(w in loc_lower for w in ["india", "mumbai", "pune", "bangalore", "bengaluru", "hyderabad", "chennai", "noida", "gurgaon", "delhi"]):
            return False, 0, "International Onsite"

        # Other locations in India (like Delhi, Kolkata, etc.)
        return True, 70, "Other India location"

    def _matches_location(self, location: str) -> bool:
        """Compatibility wrapper for unit tests checking if a location is allowed."""
        is_valid, _, _ = self._evaluate_location(location)
        return is_valid

    def _extract_experience(self, text: str) -> int | None:
        """
        Extract required years of experience from description using regex.
        Returns the minimum required experience found (lower bound in ranges).
        """
        if not text:
            return None

        text_clean = text.replace('\xa0', ' ')

        # 1. Look for range patterns first, e.g. "2-5 years", "2 to 4 years"
        range_patterns = [
            r"(\d+)\s*(?:-|to)\s*(\d+)\s*(?:years?|yrs?)\b",
            r"(?:experience\s*of\s*|experience:\s*)?(\d+)\s*(?:-|to)\s*(\d+)\s*(?:years?|yrs?)\b"
        ]
        
        min_years = None
        
        for pattern in range_patterns:
            matches = re.findall(pattern, text_clean, re.IGNORECASE)
            for m in matches:
                try:
                    low = int(m[0])
                    if min_years is None or low < min_years:
                        min_years = low
                except (ValueError, IndexError):
                    continue

        # 2. Look for single value patterns, e.g. "3+ years", "3 years of experience", "minimum 3 years"
        if min_years is None:
            single_patterns = [
                r"(\d+)\+?\s*(?:years?|yrs?)(?:\s+of)?\s+experience\b",
                r"experience\s*(?:of|required|level)?\s*(?::\s*)?(\d+)\+?\s*(?:years?|yrs?)\b",
                r"(?:minimum|min|at least|require[sd]?)\s*(?:of\s*)?(\d+)\+?\s*(?:years?|yrs?)\b",
                r"(?:have|possess)\s+(\d+)\+?\s*(?:years?|yrs?)\b"
            ]
            for pattern in single_patterns:
                matches = re.findall(pattern, text_clean, re.IGNORECASE)
                for m in matches:
                    try:
                        years = int(m)
                        if min_years is None or years < min_years:
                            min_years = years
                    except ValueError:
                        continue

        return min_years

    def _evaluate_experience(self, title: str, description: str) -> tuple[bool, int, str]:
        """
        Evaluate experience constraints and calculate score (max 20 points).
        Returns (is_accepted, score, reason).
        """
        title_lower = title.lower()
        desc_lower = description.lower() if description else ""

        # Check if title indicates an entry-level/fresher role
        entry_title_keywords = ["graduate", "associate", "fresher", "entry-level", "entry level", "junior", "trainee", "intern", "internship"]
        is_entry_title = any(kw in title_lower for kw in entry_title_keywords)

        # Check if description indicates entry-level
        entry_desc_keywords = ["fresher", "no experience required", "entry level", "entry-level", "freshers welcome"]
        is_entry_desc = any(kw in desc_lower for kw in entry_desc_keywords)

        is_entry_role = is_entry_title or is_entry_desc

        exp_years = self._extract_experience(description)

        if exp_years is not None and exp_years > self._profile.max_experience_years:
            if is_entry_role:
                return True, 20, f"Experience {exp_years} yrs > max {self._profile.max_experience_years} but accepted as entry-level role"
            else:
                return False, 0, f"Experience required ({exp_years} yrs) exceeds max ({self._profile.max_experience_years} yrs)"

        if exp_years is not None:
            return True, 20, f"Experience within range ({exp_years} yrs)"
        else:
            return True, 20, "Experience not mentioned (default match)"

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

    def classify_role(self, title: str, description: str) -> dict[str, Any]:
        """
        Classifies a job listing into one of 11 categories and calculates confidence.
        """
        title_lower = title.lower()
        desc_lower = description.lower() if description else ""
        
        # Categories mapping
        categories = {
            "GENAI_ENGINEERING": {
                "title_patterns": [r"\bgenai\b", r"\bgenerative\s+ai\b", r"\bllm\b", r"\bprompt\s+engineer\b"],
                "desc_patterns": [r"\bllm\b", r"\bgenerative\s+ai\b", r"\bgenai\b", r"\bprompt\s+engineering\b", r"\blangchain\b", r"\bllamaindex\b", r"\btransformers\b", r"\bgpt\b", r"\bclaude\b", r"\bgemini\b", r"\bopenai\b"]
            },
            "NLP_ENGINEERING": {
                "title_patterns": [r"\bnlp\b", r"\bnatural\s+language\b"],
                "desc_patterns": [r"\bnlp\b", r"\bnatural\s+language\s+processing\b", r"\bspacy\b", r"\bnltk\b", r"\bbert\b"]
            },
            "COMPUTER_VISION": {
                "title_patterns": [r"\bcomputer\s+vision\b", r"\bcv\b"],
                "desc_patterns": [r"\bcomputer\s+vision\b", r"\bopencv\b", r"\byolo\b", r"\bcnn\b", r"\bimage\s+processing\b", r"\bobject\s+detection\b", r"\bsrcnn\b", r"\bgan\b"]
            },
            "ML_ENGINEERING": {
                "title_patterns": [r"\bml\b", r"\bmachine\s+learning\b", r"\bdeep\s+learning\b"],
                "desc_patterns": [r"\bpytorch\b", r"\btensorflow\b", r"\bkeras\b", r"\bscikit-learn\b", r"\bmachine\s+learning\b", r"\bmlops\b", r"\bmodel\s+training\b", r"\bdeep\s+learning\b"]
            },
            "AI_ENGINEERING": {
                "title_patterns": [r"\bai\b", r"\bartificial\s+intelligence\b"],
                "desc_patterns": [r"\bartificial\s+intelligence\b", r"\bai\s+engineer\b", r"\bai\s+developer\b", r"\bai\s+application\b", r"\bapplied\s+ai\b"]
            },
            "DATA_SCIENCE": {
                "title_patterns": [r"\bdata\s+scientist\b", r"\bdata\s+science\b"],
                "desc_patterns": [r"\bdata\s+science\b", r"\bpandas\b", r"\bnumpy\b", r"\bscikit-learn\b", r"\bjupyter\b"]
            },
            "PYTHON_BACKEND": {
                "title_patterns": [r"\bpython\b", r"\bbackend\b"],
                "desc_patterns": [r"\bpython\b", r"\bfastapi\b", r"\bflask\b", r"\bddjango\b", r"\bbackend\b", r"\brest\s+api\b"]
            },
            "ANDROID": {
                "title_patterns": [r"\bandroid\b"],
                "desc_patterns": [r"\bandroid\b", r"\bkotlin\b", r"\bjava\b"]
            },
            "FLUTTER": {
                "title_patterns": [r"\bflutter\b"],
                "desc_patterns": [r"\bflutter\b", r"\bdart\b"]
            },
            "SOFTWARE_ENGINEERING": {
                "title_patterns": [r"\bsoftware\b", r"\bdeveloper\b", r"\bengineer\b", r"\bassociate\b", r"\bgraduate\b", r"\bmobile\b"],
                "desc_patterns": [r"\bsoftware\s+development\b", r"\bprogramming\b", r"\bgit\b", r"\bsql\b"]
            }
        }
        
        # Order of precedence for picking when scores tie
        precedence = [
            "GENAI_ENGINEERING", "NLP_ENGINEERING", "COMPUTER_VISION",
            "ML_ENGINEERING", "AI_ENGINEERING", "FLUTTER", "ANDROID",
            "PYTHON_BACKEND", "DATA_SCIENCE", "SOFTWARE_ENGINEERING"
        ]
        
        cat_scores = {cat: 0 for cat in precedence}
        title_matched_cats = set()
        
        for cat in precedence:
            patterns = categories[cat]
            t_match = False
            for p in patterns["title_patterns"]:
                if re.search(p, title_lower):
                    t_match = True
                    break
            
            d_count = 0
            for p in patterns["desc_patterns"]:
                if re.search(p, desc_lower):
                    d_count += 1
            
            if t_match:
                cat_scores[cat] += 100
                title_matched_cats.add(cat)
            
            cat_scores[cat] += d_count * 10
            
        best_cat = "OTHER"
        best_score = 0
        
        for cat in precedence:
            if cat_scores[cat] > best_score:
                best_score = cat_scores[cat]
                best_cat = cat
                
        if best_cat == "OTHER":
            return {"category": "OTHER", "confidence": 0}
            
        patterns = categories[best_cat]
        desc_matches = sum(1 for p in patterns["desc_patterns"] if re.search(p, desc_lower))
        
        if best_cat in title_matched_cats:
            confidence = min(100, 90 + desc_matches)
        else:
            confidence = min(89, 70 + desc_matches)
            
        return {"category": best_cat, "confidence": confidence}

    def _get_company_priority(self, company: str) -> int:
        comp_lower = company.lower().strip()
        
        # New requirements:
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

        # Check for month indicators
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

            # 1. Hard Exclusion: Title keywords (senior/lead conditional check + non-tech exclusions)
            is_valid_title, title_reason = self._check_title_exclusions(title, exp_years)
            if not is_valid_title:
                self.logger.info(f"Rejected:\nTitle: {title}\nCompany: {company}\nReason: ROLE")
                continue

            # 2. Hard Exclusion: Location
            is_valid_loc, loc_score, loc_reason = self._evaluate_location(listing.location)
            if not is_valid_loc or loc_score == 0:
                self.logger.info(f"Rejected:\nTitle: {title}\nCompany: {company}\nReason: LOCATION")
                continue

            # 3. Target Title Match Check
            if not self._matches_title_phrases(title):
                self.logger.info(f"Rejected:\nTitle: {title}\nCompany: {company}\nReason: ROLE")
                continue

            # 4. Experience Range Check
            is_valid_exp, raw_exp_score, exp_reason = self._evaluate_experience(title, listing.description)
            if not is_valid_exp:
                self.logger.info(f"Rejected:\nTitle: {title}\nCompany: {company}\nReason: EXPERIENCE")
                continue

            # 5. Role Classification
            classification = self.classify_role(title, listing.description)
            role_category = classification["category"]
            role_score = classification["confidence"] if role_category != "OTHER" else 0

            # 6. Skill Score
            raw_skill_score, matched_skills = self._calculate_skill_score(title, listing.description)
            normalized_skill_score = min(100, len(matched_skills) * 20)

            # 7. Total Weighted Job Score
            # Formula: job_score = 0.30 * role_score + 0.25 * location_score + 0.20 * skill_score + 0.15 * company_score + 0.10 * freshness_score
            company_score = self._get_company_priority(company)
            freshness_score = self._calculate_freshness_score(listing.posted_date)
            
            job_score = (
                0.30 * role_score +
                0.25 * loc_score +
                0.20 * normalized_skill_score +
                0.15 * company_score +
                0.10 * freshness_score
            )
            job_score = round(job_score, 1)

            # 8. Check Job Score Threshold
            if job_score >= 60:
                listing.role_category = role_category
                listing.job_score = job_score
                listing.company_priority = company_score
                
                # Classification labels:
                if job_score >= 90:
                    listing.status = "Excellent"
                elif job_score >= 80:
                    listing.status = "Strong"
                elif job_score >= 70:
                    listing.status = "Good"
                else:
                    listing.status = "Potential"
                    
                relevant_listings.append(listing)
            else:
                reason = "SKILLS" if normalized_skill_score < 50 else "ROLE"
                self.logger.info(f"Rejected:\nTitle: {title}\nCompany: {company}\nReason: {reason}")

        self.logger.info(
            f"Relevance filtering finished: {len(listings)} input -> "
            f"{len(relevant_listings)} relevant (filtered {len(listings) - len(relevant_listings)} irrelevant)"
        )
        return relevant_listings
