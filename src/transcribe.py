"""Whisper transcription wrapper for local speech-to-text."""

import logging
import os
import numpy as np
from typing import Optional

logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """Wraps OpenAI's Whisper for local speech-to-text transcription."""

    def __init__(
        self,
        model_name: str = "base",
        language: str = "en",
        device: str = "cpu",
    ):
        """
        Initialize Whisper transcriber.

        Args:
            model_name: Model size (tiny, base, small, medium, large)
            language: Language code (e.g., "en")
            device: Device to use ("cpu" or "cuda")
        """
        self.model_name = model_name
        self.language = language
        self.device = device
        self.model = None

        self._init_model()

    def _init_model(self) -> None:
        """Initialize the Whisper model."""
        try:
            import whisper

            logger.info(f"Loading Whisper model: {self.model_name}")

            # Load the model (will auto-download if not present)
            self.model = whisper.load_model(
                self.model_name,
                device=self.device,
                download_root="models",
            )
            logger.info("Whisper model loaded successfully")

        except ImportError:
            logger.error(
                "openai-whisper not installed. Install with: pip install openai-whisper"
            )
            raise
        except Exception as e:
            logger.error(f"Error loading Whisper model: {e}")
            raise

    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """
        Transcribe audio data to text.

        Args:
            audio_data: NumPy array of audio samples (float32, -1.0 to 1.0)
            sample_rate: Sample rate of the audio (default 16000)

        Returns:
            Transcribed text
        """
        if self.model is None:
            logger.error("Model not initialized")
            return ""

        try:
            # Ensure audio is in the correct format
            if audio_data.dtype != np.float32:
                audio_data = audio_data.astype(np.float32)

            # Normalize to -1.0 to 1.0 range if needed
            max_val = np.max(np.abs(audio_data))
            if max_val > 0 and max_val > 1.0:
                audio_data = audio_data / max_val

            # Whisper expects audio in the range [-1, 1] and resamples to 16000 Hz internally
            logger.debug(f"Transcribing audio ({len(audio_data)} samples at {sample_rate} Hz)")

            # Transcribe using the model
            result = self.model.transcribe(
                audio_data,
                language=self.language,
                verbose=False,
            )

            text = result.get("text", "").strip()
            logger.info(f"Transcription: {text}")

            return text

        except Exception as e:
            logger.error(f"Error during transcription: {e}")
            import traceback
            traceback.print_exc()
            return ""

    def transcribe_file(self, filepath: str) -> str:
        """
        Transcribe an audio file.

        Args:
            filepath: Path to the audio file

        Returns:
            Transcribed text
        """
        try:
            if self.model is None:
                logger.error("Model not initialized")
                return ""

            logger.debug(f"Transcribing file: {filepath}")

            result = self.model.transcribe(
                filepath,
                language=self.language,
                verbose=False,
            )

            text = result.get("text", "").strip()
            logger.info(f"File transcription: {text}")

            return text

        except Exception as e:
            logger.error(f"Error transcribing file {filepath}: {e}")
            import traceback
            traceback.print_exc()
            return ""
