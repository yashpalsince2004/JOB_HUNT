"""Agents package for AI Job Hunter."""

from agents.base_agent import BaseAgent
from agents.scraper_agent import ScraperAgent
from agents.dedup_agent import DedupAgent
from agents.relevance_agent import RelevanceAgent
from agents.jd_analysis_agent import JDAnalysisAgent
from agents.ats_scoring_agent import ATSScoringAgent
from agents.resume_agent import ResumeAgent
from agents.cover_letter_agent import CoverLetterAgent
from agents.interview_agent import InterviewAgent
from agents.recruiter_agent import RecruiterAgent
from agents.skill_gap_agent import SkillGapAgent

__all__ = [
    "BaseAgent",
    "ScraperAgent",
    "DedupAgent",
    "RelevanceAgent",
    "JDAnalysisAgent",
    "ATSScoringAgent",
    "ResumeAgent",
    "CoverLetterAgent",
    "InterviewAgent",
    "RecruiterAgent",
    "SkillGapAgent",
]
