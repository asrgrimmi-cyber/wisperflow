"""Whisper.cpp transcription wrapper for local speech-to-text."""

import logging
import os
import numpy as np
from typing import Optional

logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """Wraps whisper.cpp for local speech-to-text transcription."""

    def __init__(
        self,
        model_path: str = "models/ggml-base.en.bin",
        model_name: str = "base",
        language: str = "en",
        device: str = "cpu",
    ):
        """
        Initialize Whisper transcriber.

        Args:
            model_path: Path to GGML model file
            model_name: Model size (tiny, base, small, medium, large)
            language: Language code (e.g., "en")
            device: Device to use ("cpu" or "cuda")
        """
        self.model_path = model_path
        self.model_name = model_name
        self.language = language
        self.device = device
        self.model = None

        self._init_model()

    def _init_model(self) -> None:
        """Initialize the whisper.cpp model."""
        try:
            from pywhispercpp.factory import model_factory

            logger.info(f"Loading Whisper model: {self.model_name}")

            # Download model if not present
            if not os.path.exists(self.model_path):
                logger.info(f"Model not found at {self.model_path}, downloading...")
                os.makedirs(os.path.dirname(self.model_path), exist_ok=True)
                self._download_model()

            # Load the model
            self.model = model_factory(
                model_name=self.model_name,
                models_dir="models",
            )
            logger.info("Whisper model loaded successfully")

        except ImportError:
            logger.error(
                "pywhispercpp not installed. Install with: pip install pywhispercpp"
            )
            raise
        except Exception as e:
            logger.error(f"Error loading Whisper model: {e}")
            raise

    def _download_model(self) -> None:
        """Download the Whisper model from OpenAI."""
        try:
            from pywhispercpp.factory import model_factory

            # This will download the model automatically
            model_factory(
                model_name=self.model_name,
                models_dir="models",
            )
            logger.info(f"Model {self.model_name} downloaded successfully")
        except Exception as e:
            logger.error(f"Error downloading model: {e}")
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
            if max_val > 1.0:
                audio_data = audio_data / (max_val + 1e-6)

            logger.debug(f"Transcribing audio ({len(audio_data)} samples)")

            # Transcribe
            result = self.model.transcribe(
                audio_data,
                language=self.language,
            )

            text = result.get("text", "").strip()
            logger.info(f"Transcription: {text}")

            return text

        except Exception as e:
            logger.error(f"Error during transcription: {e}")
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
            import soundfile as sf

            audio_data, sample_rate = sf.read(filepath)

            # Handle stereo -> mono conversion
            if len(audio_data.shape) > 1:
                audio_data = np.mean(audio_data, axis=1)

            return self.transcribe(audio_data, sample_rate)

        except Exception as e:
            logger.error(f"Error transcribing file {filepath}: {e}")
            return ""
