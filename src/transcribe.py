"""Whisper transcription wrapper — remote GPU with automatic CPU fallback."""

import logging
import threading
import numpy as np
import requests
from typing import Optional

logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """Transcribes audio via remote GPU server, falls back to local CPU if unavailable."""

    def __init__(
        self,
        model_name: str = "base",
        language: str = "en",
        device: str = "cpu",
        remote_url: Optional[str] = None,
        remote_timeout: int = 30,
    ):
        self.model_name = model_name
        self.language = language
        self.device = device
        self.remote_url = remote_url
        self.remote_timeout = remote_timeout
        self.model = None
        self._remote_healthy = False
        self._local_loading = False

        # Check remote first — if GPU is up, defer local model to background
        if self.remote_url:
            self._remote_healthy = self._check_remote()

        if self._remote_healthy:
            # GPU is up — try loading local model in background as fallback
            logger.info("GPU server healthy, loading local CPU model in background...")
            self._local_loading = True
            t = threading.Thread(target=self._init_model_background, daemon=True)
            t.start()
        else:
            # No GPU server — try loading local model (may fail if torch not installed)
            try:
                self._init_model()
            except Exception as e:
                logger.warning(f"Local model unavailable: {e}")
                logger.warning("No GPU server and no local model — transcription will not work")

    def _check_remote(self) -> bool:
        """Check if the remote GPU server is reachable."""
        try:
            resp = requests.get(f"{self.remote_url}/health", timeout=5)
            if resp.ok:
                logger.info(f"Remote GPU server is healthy at {self.remote_url}")
                return True
            logger.warning(f"Remote server returned {resp.status_code}")
            return False
        except Exception as e:
            logger.warning(f"Remote GPU server unreachable ({e}), will use local CPU")
            return False

    def _init_model_background(self) -> None:
        """Load local model in background thread."""
        try:
            self._init_model()
        except Exception as e:
            logger.warning(f"Background model load failed: {e}")
        finally:
            self._local_loading = False

    def _init_model(self) -> None:
        """Initialize the local Whisper model (CPU fallback)."""
        try:
            import whisper

            logger.info(f"Loading local Whisper model: {self.model_name} (CPU fallback)")
            self.model = whisper.load_model(
                self.model_name,
                device=self.device,
                download_root="models",
            )
            logger.info("Local Whisper model loaded successfully")

        except ImportError:
            logger.error(
                "openai-whisper not installed. Install with: pip install openai-whisper"
            )
            raise
        except Exception as e:
            logger.error(f"Error loading Whisper model: {e}")
            raise

    def transcribe(self, audio_data: np.ndarray, sample_rate: int = 16000) -> str:
        """Transcribe audio — tries remote GPU first, falls back to local CPU."""
        # Normalize audio once
        if audio_data.dtype != np.float32:
            audio_data = audio_data.astype(np.float32)
        max_val = np.max(np.abs(audio_data))
        if max_val > 0 and max_val > 1.0:
            audio_data = audio_data / max_val

        # Try remote GPU first
        if self.remote_url:
            text = self._transcribe_remote(audio_data, sample_rate)
            if text is not None:
                return text
            # Remote failed — fall back to local
            logger.warning("Remote GPU failed, falling back to local CPU transcription")

        return self._transcribe_local(audio_data, sample_rate)

    def _transcribe_remote(self, audio_data: np.ndarray, sample_rate: int) -> Optional[str]:
        """Send audio to remote GPU server. Returns None on failure (triggers fallback)."""
        try:
            logger.debug(f"Sending {len(audio_data)} samples to remote GPU server")

            resp = requests.post(
                f"{self.remote_url}/transcribe",
                data=audio_data.tobytes(),
                headers={"Content-Type": "application/octet-stream"},
                params={"sample_rate": sample_rate},
                timeout=self.remote_timeout,
            )

            if resp.ok:
                result = resp.json()
                text = result.get("text", "").strip()
                server_time = result.get("time", "?")
                logger.info(f"[GPU] Transcribed in {server_time}s: {text}")
                self._remote_healthy = True
                return text

            logger.error(f"Remote server error {resp.status_code}: {resp.text}")
            self._remote_healthy = False
            return None

        except requests.Timeout:
            logger.error("Remote GPU transcription timed out")
            self._remote_healthy = False
            return None
        except Exception as e:
            logger.error(f"Remote GPU error: {e}")
            self._remote_healthy = False
            return None

    def _transcribe_local(self, audio_data: np.ndarray, sample_rate: int) -> str:
        """Transcribe using the local Whisper model on CPU."""
        if self.model is None:
            logger.error("Local model not initialized")
            return ""

        try:
            logger.info("[CPU] Transcribing locally (this may be slower)...")

            result = self.model.transcribe(
                audio_data,
                language=self.language,
                verbose=False,
            )

            text = result.get("text", "").strip()
            logger.info(f"[CPU] Transcription: {text}")
            return text

        except Exception as e:
            logger.error(f"Local transcription error: {e}")
            import traceback
            traceback.print_exc()
            return ""

    def transcribe_file(self, filepath: str) -> str:
        """Transcribe an audio file (local only)."""
        try:
            if self.model is None:
                logger.error("Model not initialized")
                return ""

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
