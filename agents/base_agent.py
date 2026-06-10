"""
Base agent module for the AI Job Hunter pipeline.

All processing agents (Scraper, Dedup, Relevance, JD Analysis, etc.)
inherit from BaseAgent.
"""

import time
from abc import ABC, abstractmethod
from typing import Any

from utils.logger import get_logger


class BaseAgent(ABC):
    """
    Abstract base class for pipeline agents.

    Provides logging, timing, and standardized run wrapper.
    """

    def __init__(self) -> None:
        self.logger = get_logger(f"agent.{self.name}")

    @property
    @abstractmethod
    def name(self) -> str:
        """Name of the agent for logging and configuration."""
        ...

    @abstractmethod
    def run(self, *args: Any, **kwargs: Any) -> Any:
        """
        Execute the agent's core logic.

        Args:
            *args: Input arguments.
            **kwargs: Input keyword arguments.

        Returns:
            Processed output data for the next stage.
        """
        ...

    def execute(self, *args: Any, **kwargs: Any) -> Any:
        """Wrapper around run() that adds logging and timing."""
        self.logger.info(f"Starting execution...")
        start_time = time.time()
        try:
            output = self.run(*args, **kwargs)
            duration = time.time() - start_time
            self.logger.info(f"Completed execution in {duration:.2f}s")
            return output
        except Exception as e:
            self.logger.error(f"Failed during execution: {e}", exc_info=True)
            raise
