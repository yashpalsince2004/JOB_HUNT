"""
Unified LLM client with Gemini 2.5 Flash primary and Ollama fallback.

Handles:
  - Structured JSON output via Gemini's response schema
  - Automatic retry with exponential backoff on 429s
  - Graceful fallback to local Ollama when Gemini quota is exhausted
  - Rate limiting integration
"""

import json
import re
from typing import Any

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from utils.logger import get_logger
from utils.rate_limiter import rate_limiter

logger = get_logger("llm_client")


class LLMError(Exception):
    """Raised when both Gemini and Ollama fail."""
    pass


class LLMClient:
    """
    Unified LLM interface — Gemini primary, Ollama fallback.

    Usage:
        client = LLMClient(api_key="...", model="gemini-2.5-flash")

        # Structured output
        result = client.generate_json(
            prompt="Analyze this job description...",
            system_prompt="You are a JD analyzer.",
        )

        # Free-form text
        text = client.generate_text("Write a cover letter for...")
    """

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
        ollama_base_url: str = "http://localhost:11434",
        ollama_model: str = "llama3.1",
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._ollama_base_url = ollama_base_url
        self._ollama_model = ollama_model
        self._gemini_client = None
        self._gemini_available = bool(api_key)
        
        # State tracking fields for diagnostic output
        self.llm_provider_used = "none"
        self.fallback_available = False
        self.fallback_status = "Offline"
        self.fallback_error = None

        if self._gemini_available:
            try:
                from google import genai
                self._gemini_client = genai.Client(api_key=api_key)
                logger.info(f"Gemini client initialized with model: {model}")
            except ImportError:
                logger.warning("google-genai not installed, Gemini unavailable")
                self._gemini_available = False
            except Exception as e:
                logger.warning(f"Failed to initialize Gemini: {e}")
                self._gemini_available = False

        # Run startup health check for Ollama
        self.check_ollama_status()

    def check_ollama_status(self) -> None:
        """Startup health check for Ollama server and model availability."""
        import httpx
        logger.info(f"Checking Ollama status at {self._ollama_base_url}...")
        try:
            response = httpx.get(f"{self._ollama_base_url}/api/tags", timeout=2.0)
            if response.status_code == 200:
                self.fallback_available = True
                data = response.json()
                models = [m.get("name") for m in data.get("models", [])]
                
                # Check for target model matching
                target = self._ollama_model
                model_found = False
                for m in models:
                    if m == target or m.split(":")[0] == target.split(":")[0]:
                        model_found = True
                        break
                
                if model_found:
                    self.fallback_status = "Ready"
                    logger.info(f"Ollama fallback is available and model '{self._ollama_model}' is ready.")
                else:
                    self.fallback_status = "Degraded"
                    logger.warning(
                        f"Ollama is running, but model '{self._ollama_model}' was not found. "
                        f"Available models: {models}"
                    )
            else:
                self.fallback_available = False
                self.fallback_status = "Offline"
                self.fallback_error = f"HTTP status {response.status_code}"
                logger.warning(f"Ollama server health check returned status {response.status_code}")
        except Exception as e:
            self.fallback_available = False
            self.fallback_status = "Offline"
            self.fallback_error = str(e)
            logger.warning(f"Ollama health check failed: {e}. Fallback disabled.")

    @retry(
        retry=retry_if_exception_type(Exception),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=4, max=60),
        reraise=True,
    )
    def _call_gemini(self, prompt: str, system_prompt: str | None = None) -> str:
        """Call Gemini API with retry logic."""
        if self._gemini_client is None:
            raise LLMError("Gemini client is not initialized.")

        rate_limiter.wait_sync("gemini")

        contents = prompt
        config = {}
        if system_prompt:
            config["system_instruction"] = system_prompt

        response = self._gemini_client.models.generate_content(
            model=self._model,
            contents=contents,
            config=config if config else None,
        )
        self.llm_provider_used = "gemini"
        return response.text

    def _call_ollama(self, prompt: str, system_prompt: str | None = None) -> str:
        """Call local Ollama instance as fallback."""
        import httpx

        if not self.fallback_available:
            raise LLMError("Ollama fallback is not available (offline or failed status checks).")

        logger.info(f"Falling back to Ollama ({self._ollama_model})")

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = httpx.post(
                f"{self._ollama_base_url}/api/chat",
                json={
                    "model": self._ollama_model,
                    "messages": messages,
                    "stream": False,
                },
                timeout=120.0,
            )
            response.raise_for_status()
            self.llm_provider_used = "ollama"
            return response.json()["message"]["content"]
        except Exception as e:
            self.llm_provider_used = "none"
            raise LLMError(f"Ollama also failed: {e}") from e

    def generate_text(self, prompt: str, system_prompt: str | None = None) -> str:
        """
        Generate free-form text from the LLM.

        Tries Gemini first, falls back to Ollama on failure.

        Args:
            prompt: The user prompt.
            system_prompt: Optional system instruction.

        Returns:
            Generated text string.

        Raises:
            LLMError: If both Gemini and Ollama fail.
        """
        # Try Gemini first
        if self._gemini_available:
            try:
                return self._call_gemini(prompt, system_prompt)
            except Exception as e:
                logger.warning(f"Gemini failed after retries: {e}")
                # Disable Gemini for the remainder of this run if quota is exhausted
                if "RESOURCE_EXHAUSTED" in str(e) or "429" in str(e):
                    logger.warning("Gemini quota exhausted/rate-limited. Disabling Gemini for the remainder of this run.")
                    self._gemini_available = False

        # Fallback to Ollama
        return self._call_ollama(prompt, system_prompt)

    def generate_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
    ) -> dict[str, Any]:
        """
        Generate structured JSON output from the LLM.

        Instructs the model to respond in JSON and parses the result.

        Args:
            prompt: The user prompt.
            system_prompt: Optional system instruction.

        Returns:
            Parsed JSON as a dictionary.

        Raises:
            LLMError: If both models fail or output is not valid JSON.
        """
        json_instruction = (
            "\n\nIMPORTANT: Respond ONLY with valid JSON. "
            "Do not include markdown formatting, code blocks, or any other text. "
            "Output raw JSON only."
        )

        enhanced_prompt = prompt + json_instruction
        raw_text = self.generate_text(enhanced_prompt, system_prompt)

        # Clean up common LLM formatting issues
        cleaned = raw_text.strip()

        # Remove markdown code blocks if present
        if cleaned.startswith("```"):
            # Remove opening ```json or ``` and closing ```
            cleaned = re.sub(r"^```(?:json)?\s*\n?", "", cleaned)
            cleaned = re.sub(r"\n?```\s*$", "", cleaned)
            cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM output as JSON: {e}")
            logger.debug(f"Raw output was: {raw_text[:500]}")
            raise LLMError(f"LLM returned invalid JSON: {e}") from e
