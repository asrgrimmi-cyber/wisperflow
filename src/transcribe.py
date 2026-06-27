"""Whisper transcription — local CPU/GPU only."""

import logging
import numpy as np

logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """Transcribes audio using local Whisper model (CPU or local GPU)."""

    def __init__(
        self,
        model_name: str = "base",
        language: str = "en",
        device: str = "cpu",
        **kwargs,  # Ignore remote_url and remote_timeout for backwards compatibility
    ):
        self.model_name = model_name
        self.language = language
        self.device = device
        self.model = None

        # Initialize local model immediately
        try:
            self._init_model()
        except Exception as e:
            logger.error(f"Failed to initialize Whisper model: {e}")
            raise

    def _init_model(self) -> None:
        """Initialize the local Whisper model."""
        try:
            import whisper

            logger.info(f"Loading Whisper model: {self.model_name} (device: {self.device})")
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
        """Transcribe audio using local Whisper model."""
        if self.model is None:
            logger.error("Model not initialized")
            return ""

        # Normalize audio
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)
        max_val = np.max(np.abs(audio_data))
        if max_val > 0 and max_val > 1.0:
            audio_data = audio_data / max_val

        try:
            logger.info(f"Transcribing audio ({len(audio_data)} samples)...")

            result = self.model.transcribe(
                audio_data,
                language=self.language,
                verbose=False,
            )

            text = result.get("text", "").strip()
            logger.info(f"Transcription: {text}")
            return text

        except Exception as e:
            logger.error(f"Transcription error: {e}")
            import traceback
            traceback.print_exc()
            return ""

    def transcribe_file(self, filepath: str) -> str:
        """Transcribe an audio file."""
        if self.model is None:
            logger.error("Model not initialized")
            return ""

        try:
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
            return ""
