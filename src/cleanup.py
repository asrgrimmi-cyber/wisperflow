"""Ollama-based LLM cleanup for fixing transcription formatting."""

import logging
import requests
from typing import Optional

logger = logging.getLogger(__name__)


class OllamaCleanup:
    """Cleans up raw transcription text using Ollama."""

    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "llama2",
        timeout: int = 10,
        prompt_template: Optional[str] = None,
    ):
        """
        Initialize Ollama cleanup.

        Args:
            base_url: Base URL of Ollama API
            model: Model name to use for cleanup
            timeout: Timeout in seconds for API requests
            prompt_template: Custom prompt template (use {text} as placeholder)
        """
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.prompt_template = (
            prompt_template
            or """Rules: Output ONLY the corrected text. No quotes, no explanations, no preamble. Fix grammar and punctuation only. Keep all original meaning.

{text}"""
        )

    def is_available(self) -> bool:
        """Check if Ollama is available."""
        try:
            response = requests.get(
                f"{self.base_url}/api/tags", timeout=self.timeout
            )
            return response.status_code == 200
        except (requests.ConnectionError, requests.Timeout):
            return False

    def cleanup(self, text: str) -> str:
        """
        Clean up transcription using Ollama.

        Args:
            text: Raw transcription text

        Returns:
            Cleaned up text
        """
        if not text.strip():
            return text

        if not self.is_available():
            logger.warning(
                "Ollama not available, returning raw text"
            )
            return text

        try:
            logger.debug(f"Sending cleanup request to Ollama ({self.model})")

            response = requests.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a text corrector. You receive speech-to-text output. Fix grammar and punctuation. Output ONLY the corrected sentence. Never add explanations, quotes, or commentary.",
                        },
                        {"role": "user", "content": text},
                    ],
                    "stream": False,
                    "options": {"num_predict": 100},
                },
                timeout=self.timeout,
            )

            if response.status_code == 200:
                result = response.json()
                cleaned_text = result.get("message", {}).get("content", "").strip()
                # Strip quotes the LLM might wrap around the text
                cleaned_text = cleaned_text.strip('"\'')
                logger.debug(f"Cleaned text: {cleaned_text}")
                return cleaned_text if cleaned_text else text
            else:
                logger.error(f"Ollama error: {response.status_code}")
                return text

        except requests.Timeout:
            logger.warning("Ollama request timed out, returning raw text")
            return text
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return text

    def cleanup_openai_compat(self, text: str) -> str:
        """
        Clean up transcription using Ollama's OpenAI-compatible API.

        Args:
            text: Raw transcription text

        Returns:
            Cleaned up text
        """
        if not text.strip():
            return text

        if not self.is_available():
            logger.warning("Ollama not available, returning raw text")
            return text

        try:
            prompt = self.prompt_template.format(text=text)

            logger.debug(
                f"Sending cleanup request to Ollama OpenAI API ({self.model})"
            )

            response = requests.post(
                f"{self.base_url}/v1/chat/completions",
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=self.timeout,
            )

            if response.status_code == 200:
                result = response.json()
                cleaned_text = (
                    result.get("choices", [{}])[0]
                    .get("message", {})
                    .get("content", "")
                    .strip()
                )
                logger.debug(f"Cleaned text: {cleaned_text}")
                return cleaned_text
            else:
                logger.error(f"Ollama error: {response.status_code}")
                return text

        except requests.Timeout:
            logger.warning("Ollama request timed out, returning raw text")
            return text
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return text
