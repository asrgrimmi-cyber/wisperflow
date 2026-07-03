"""Whisper transcription — using faster-whisper with OpenVINO for Intel GPU support."""

import logging
import numpy as np

logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """Transcribes audio using faster-whisper (OpenVINO backend for Intel GPU)."""

    def __init__(
        self,
        model_name: str = "base",
        language: str = "en",
        device: str = "auto",
        **kwargs,
    ):
        self.model_name = model_name
        self.language = language
        self.device = device
        self.model = None

        # Initialize local model, fall back to CPU if needed
        try:
            self._init_model()
        except Exception as e:
            if self.device != "cpu":
                logger.warning(f"{self.device} failed ({e}), falling back to CPU")
                self.device = "cpu"
                self._init_model()
            else:
                logger.error(f"Failed to initialize Whisper model: {e}")
                raise

    def _init_model(self) -> None:
        """Initialize the faster-whisper model."""
        try:
            from faster_whisper import WhisperModel

            # Map device config to faster-whisper compute type and device
            if self.device in ("auto", "openvino", "xpu"):
                device = "auto"
                compute_type = "int8"
            elif self.device == "cpu":
                device = "cpu"
                compute_type = "int8"
            elif self.device == "cuda":
                device = "cuda"
                compute_type = "float16"
            else:
                device = "cpu"
                compute_type = "int8"

            logger.info(f"Loading faster-whisper model: {self.model_name} (device: {device}, compute: {compute_type})")
            self.model = WhisperModel(
                self.model_name,
                device=device,
                compute_type=compute_type,
                download_root="models",
            )
            logger.info(f"Whisper model loaded successfully (device: {device})")

        except ImportError:
            logger.error(
                "faster-whisper not installed. Install with: pip install faster-whisper openvino"
            )
            raise
        except Exception as e:
            logger.error(f"Error loading Whisper model: {e}")
            raise

    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """Transcribe audio using faster-whisper."""
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

            segments, info = self.model.transcribe(
                audio_data,
                language=self.language,
                initial_prompt="This is a dictation. Use proper grammar, spelling, and punctuation.",
                condition_on_previous_text=False,
                temperature=0.0,
                beam_size=1,
                vad_filter=True,
            )

            text = " ".join(seg.text.strip() for seg in segments).strip()
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
            segments, info = self.model.transcribe(
                filepath,
                language=self.language,
                initial_prompt="This is a dictation. Use proper grammar, spelling, and punctuation.",
                condition_on_previous_text=False,
                temperature=0.0,
                beam_size=1,
                vad_filter=True,
            )

            text = " ".join(seg.text.strip() for seg in segments).strip()
            logger.info(f"File transcription: {text}")
            return text

        except Exception as e:
            logger.error(f"Error transcribing file {filepath}: {e}")
            return ""
