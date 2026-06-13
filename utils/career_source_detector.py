"""
Career Source Detector.

Automatically discovers the ATS platform (Workday, Greenhouse, Lever, Ashby, SmartRecruiters)
for a given careers URL or defaults to custom scraping.
"""

import httpx
import re
from typing import Dict, Any
from utils.logger import get_logger

logger = get_logger("scraper.detector")


class CareerSourceDetector:
    """
    Helper to detect and map official career portal sources to their ATS platforms.
    """

    _PREDEFINED = {
        "quantiphi": {
            "company": "Quantiphi",
            "platform": "Workday",
            "career_url": "https://quantiphi.myworkdayjobs.com/Careers",
            "api_endpoint": "https://quantiphi.myworkdayjobs.com/wday/cxs/Quantiphi_Careers/Careers/jobs"
        },
        "fractal": {
            "company": "Fractal Analytics",
            "platform": "Workday",
            "career_url": "https://fractal.myworkdayjobs.com/Fractal",
            "api_endpoint": "https://fractal.myworkdayjobs.com/wday/cxs/Fractal/Fractal/jobs"
        },
        "fractal analytics": {
            "company": "Fractal Analytics",
            "platform": "Workday",
            "career_url": "https://fractal.myworkdayjobs.com/Fractal",
            "api_endpoint": "https://fractal.myworkdayjobs.com/wday/cxs/Fractal/Fractal/jobs"
        },
        "tiger analytics": {
            "company": "Tiger Analytics",
            "platform": "custom",
            "career_url": "https://apply.workable.com/tiger-analytics",
            "api_endpoint": "https://apply.workable.com/api/v3/accounts/tiger-analytics/jobs"
        },
        "tredence": {
            "company": "Tredence",
            "platform": "custom",
            "career_url": "https://tredence.ripplehire.com",
            "api_endpoint": "https://tredence.ripplehire.com"
        },
        "latentview": {
            "company": "LatentView Analytics",
            "platform": "custom",
            "career_url": "https://www.latentview.com/careers/",
            "api_endpoint": "https://www.latentview.com/careers/"
        },
        "latentview analytics": {
            "company": "LatentView Analytics",
            "platform": "custom",
            "career_url": "https://www.latentview.com/careers/",
            "api_endpoint": "https://www.latentview.com/careers/"
        },
        "mu sigma": {
            "company": "Mu Sigma",
            "platform": "custom",
            "career_url": "https://www.mu-sigma.com/careers",
            "api_endpoint": "https://www.mu-sigma.com/careers"
        },
        "nielseniq": {
            "company": "NielsenIQ",
            "platform": "SmartRecruiters",
            "career_url": "https://careers.smartrecruiters.com/NielsenIQ",
            "api_endpoint": "https://api.smartrecruiters.com/v1/companies/NielsenIQ/postings"
        },
        "course5": {
            "company": "Course5 Intelligence",
            "platform": "custom",
            "career_url": "https://careers.c5i.ai/",
            "api_endpoint": "https://careers.c5i.ai/"
        },
        "course5 intelligence": {
            "company": "Course5 Intelligence",
            "platform": "custom",
            "career_url": "https://careers.c5i.ai/",
            "api_endpoint": "https://careers.c5i.ai/"
        },
        "gramener": {
            "company": "Gramener",
            "platform": "custom",
            "career_url": "https://gramener.com/careers/",
            "api_endpoint": "https://gramener.com/careers/"
        },
        "exl": {
            "company": "EXL",
            "platform": "custom",
            "career_url": "https://www.exlservice.com/careers",
            "api_endpoint": "https://www.exlservice.com/careers"
        },
        "talentd": {
            "company": "Talentd",
            "platform": "custom",
            "career_url": "https://www.talentd.in/jobs",
            "api_endpoint": "https://www.talentd.in/jobs"
        }
    }

    def detect(self, company_name: str, careers_url: str) -> Dict[str, Any]:
        """
        Detect the ATS platform and endpoints for a company's careers portal.

        Args:
            company_name: Name of the company.
            careers_url: Starting careers page URL.

        Returns:
            Dict containing company, platform, career_url, and api_endpoint.
        """
        key = company_name.lower().strip()
        if key in self._PREDEFINED:
            logger.info(f"Using predefined ATS configuration for {company_name}")
            return self._PREDEFINED[key]

        logger.info(f"Detecting platform for {company_name} at {careers_url}")

        # Check URL patterns first
        detected = self._check_url(careers_url)
        if detected:
            detected["company"] = company_name
            return detected

        # Follow redirects and fetch HTML
        try:
            with httpx.Client(follow_redirects=True, timeout=10.0) as client:
                res = client.get(
                    careers_url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
                    }
                )
                final_url = str(res.url)
                
                # Check final URL pattern
                detected = self._check_url(final_url)
                if detected:
                    detected["company"] = company_name
                    return detected

                # Inspect HTML content
                html = res.text
                detected = self._check_html(html, final_url)
                if detected:
                    detected["company"] = company_name
                    return detected
        except Exception as e:
            logger.warning(f"Discovery network request failed for {company_name}: {e}")

        # Default to custom
        return {
            "company": company_name,
            "platform": "custom",
            "career_url": careers_url,
            "api_endpoint": careers_url
        }

    def _check_url(self, url: str) -> Dict[str, Any] | None:
        """Check URL string for known ATS platform subdomains or patterns."""
        if "myworkdayjobs.com" in url:
            # Parse Workday tenant and external board
            match = re.search(r"https://([^.]+)\.myworkdayjobs\.com/([^/?#]+)", url)
            subdomain = match.group(1) if match else "tenant"
            board = match.group(2) if match else "External"
            return {
                "platform": "Workday",
                "career_url": url,
                "api_endpoint": f"https://{subdomain}.myworkdayjobs.com/wday/cxs/{subdomain}/{board}/jobs"
            }

        if "boards.greenhouse.io" in url:
            match = re.search(r"boards\.greenhouse\.io/([^/?#]+)", url)
            board_id = match.group(1) if match else ""
            return {
                "platform": "Greenhouse",
                "career_url": url,
                "api_endpoint": f"https://api.greenhouse.io/v1/boards/{board_id}/jobs?content=true" if board_id else ""
            }

        if "lever.co" in url:
            match = re.search(r"lever\.co/([^/?#]+)", url)
            board_id = match.group(1) if match else ""
            return {
                "platform": "Lever",
                "career_url": url,
                "api_endpoint": f"https://api.lever.co/v0/postings/{board_id}?mode=json" if board_id else ""
            }

        if "ashbyhq.com" in url:
            match = re.search(r"ashbyhq\.com/job-board/([^/?#]+)", url)
            board_id = match.group(1) if match else ""
            return {
                "platform": "Ashby",
                "career_url": url,
                "api_endpoint": f"https://api.ashbyhq.com/posting-api/job-board/{board_id}" if board_id else ""
            }

        if "smartrecruiters.com" in url:
            match = re.search(r"smartrecruiters\.com/([^/?#]+)", url)
            board_id = match.group(1) if match else ""
            return {
                "platform": "SmartRecruiters",
                "career_url": url,
                "api_endpoint": f"https://api.smartrecruiters.com/v1/companies/{board_id}/postings" if board_id else ""
            }

        return None

    def _check_html(self, html: str, url: str) -> Dict[str, Any] | None:
        """Inspect HTML content for links containing ATS platforms."""
        # Check for Workday
        match = re.search(r'href=["\'](https://[^.]+?\.myworkdayjobs\.com/.*?)(?:["\']|\?)', html)
        if match:
            return self._check_url(match.group(1))

        # Check for Greenhouse
        match = re.search(r'href=["\'](https://boards\.greenhouse\.io/.*?)(?:["\']|\?)', html)
        if match:
            return self._check_url(match.group(1))

        # Check for Lever
        match = re.search(r'href=["\'](https://jobs\.lever\.co/.*?)(?:["\']|\?)', html)
        if match:
            return self._check_url(match.group(1))

        # Check for Ashby
        match = re.search(r'href=["\'](https://(?:app\.)?ashbyhq\.com/job-board/.*?)(?:["\']|\?)', html)
        if match:
            return self._check_url(match.group(1))

        # Check for SmartRecruiters
        match = re.search(r'href=["\'](https://careers\.smartrecruiters\.com/.*?)(?:["\']|\?)', html)
        if match:
            return self._check_url(match.group(1))

        return None
