"""Audio capture and silence detection for speech-to-text."""

import logging
import sounddevice as sd
import numpy as np
import threading
from typing import Optional
from io import BytesIO
import wave

logger = logging.getLogger(__name__)


class AudioCapture:
    """Captures audio from the microphone with silence detection."""

    def __init__(
        self,
        sample_rate: int = 16000,
        channels: int = 1,
        silence_threshold: float = 0.02,
        silence_duration: float = 1.5,
    ):
        """
        Initialize audio capture.

        Args:
            sample_rate: Sample rate in Hz (default 16000)
            channels: Number of audio channels (default 1 for mono)
            silence_threshold: RMS threshold for silence detection (0.0-1.0)
            silence_duration: Seconds of silence to auto-stop recording
        """
        self.sample_rate = sample_rate
        self.channels = channels
        self.silence_threshold = silence_threshold
        self.silence_duration = silence_duration

        self.is_recording = False
        self.frames = []
        self.lock = threading.Lock()
        self.current_rms = 0.0  # Real-time RMS level for UI visualization

    def start_recording(self) -> None:
        """Start recording audio."""
        logger.debug("Starting audio recording")
        with self.lock:
            self.frames = []
            self.is_recording = True

    def stop_recording(self) -> np.ndarray:
        """
        Stop recording audio and return the captured frames.

        Returns:
            NumPy array of audio samples (1D for mono)
        """
        logger.debug("Stopping audio recording")
        with self.lock:
            self.is_recording = False
            if self.frames:
                audio_data = np.concatenate(self.frames)
                # Flatten to 1D if needed (for mono audio from sounddevice)
                if audio_data.ndim > 1:
                    audio_data = audio_data.flatten()
                return audio_data
            return np.array([])

    def record(self) -> np.ndarray:
        """
        Record audio until silence is detected.

        Returns:
            NumPy array of audio samples
        """
        logger.info("Recording audio (waiting for speech)...")
        self.start_recording()

        silence_frames = 0
        silence_frame_count = int(self.sample_rate * 0.1 / 4096)  # 0.1s chunks
        max_silence_frames = int(self.silence_duration / 0.1)

        try:
            with sd.InputStream(
                channels=self.channels,
                samplerate=self.sample_rate,
                blocksize=4096,
            ) as stream:
                while self.is_recording:
                    chunk, overflowed = stream.read(4096)

                    if overflowed:
                        logger.warning("Audio buffer overflow")

                    with self.lock:
                        self.frames.append(chunk)

                    # Compute RMS to detect silence
                    rms = np.sqrt(np.mean(chunk**2))

                    # Update real-time RMS for UI visualization
                    self.current_rms = float(rms)

                    if rms < self.silence_threshold:
                        silence_frames += 1
                        if silence_frames >= max_silence_frames:
                            logger.info("Silence detected, stopping recording")
                            self.is_recording = False
                    else:
                        silence_frames = 0

            return self.stop_recording()

        except Exception as e:
            logger.error(f"Error during audio recording: {e}")
            return np.array([])

    def save_wav(self, audio_data: np.ndarray, filepath: str) -> None:
        """
        Save audio data to a WAV file.

        Args:
            audio_data: NumPy array of audio samples
            filepath: Path to save the WAV file
        """
        try:
            import soundfile as sf
            sf.write(filepath, audio_data, self.sample_rate)
            logger.debug(f"Saved audio to {filepath}")
        except ImportError:
            # Fallback to wave module if soundfile not available
            with wave.open(filepath, "wb") as wav_file:
                wav_file.setnchannels(self.channels)
                wav_file.setsampwidth(2)
                wav_file.setframerate(self.sample_rate)
                wav_file.writeframes((audio_data * 32767).astype(np.int16).tobytes())

    def get_wav_bytes(self, audio_data: np.ndarray) -> bytes:
        """
        Convert audio data to WAV bytes.

        Args:
            audio_data: NumPy array of audio samples

        Returns:
            Bytes of WAV file
        """
        wav_buffer = BytesIO()
        with wave.open(wav_buffer, "wb") as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(2)
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes((audio_data * 32767).astype(np.int16).tobytes())

        wav_buffer.seek(0)
        return wav_buffer.getvalue()
