"""Wisper — local speech-to-text dictation tool for Windows.

Press Ctrl+Win (or click the floating island) to dictate.
Audio is sent to a GPU server for fast Whisper transcription,
with local CPU fallback. Transcribed text is pasted into the
focused window.
"""

import ctypes
import logging
import os
import sys
import threading
import time
from pathlib import Path

import yaml


def _app_dir() -> Path:
    """Return the directory containing the exe (frozen) or the project root (dev)."""
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).parent.parent


sys.path.insert(0, str(_app_dir()))

from src.audio import AudioCapture
from src.cleanup import OllamaCleanup
from src.floating_island import FloatingIsland, IslandState
from src.hotkey import HotkeyListener
from src.inject import TextInjector
from src.transcribe import WhisperTranscriber
from src.tts import TextToSpeech

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(name)s  %(levelname)s  %(message)s",
)
logger = logging.getLogger("wisper")


def _hide_console() -> None:
    """Hide the console window on Windows."""
    try:
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
    except Exception:
        pass


class WisperApp:
    """Orchestrates the capture → transcribe → inject pipeline."""

    def __init__(self, config_path: str = "config.yaml"):
        t0 = time.perf_counter()
        self.config = self._load_config(config_path)
        self.is_running = False
        self.is_listening = False
        self._processing = False
        self._process_lock = threading.Lock()
        self._recording_event = threading.Event()
        self._audio_ready = threading.Event()
        self._last_audio = None

        logger.info("Initializing Wisper")

        # UI
        self.island = FloatingIsland(
            on_click=self._on_island_click,
            on_right_click=self._pause,
            on_exit=self._stop,
        )
        # Audio
        audio_cfg = self.config["audio"]
        self.audio = AudioCapture(
            sample_rate=audio_cfg["sample_rate"],
            channels=audio_cfg["channels"],
            silence_threshold=audio_cfg["silence_threshold"],
            silence_duration=audio_cfg["silence_duration"],
        )

        # Transcription
        whisper_cfg = self.config["whisper"]
        self.transcriber = WhisperTranscriber(
            model_name=whisper_cfg["model_name"],
            language=whisper_cfg["language"],
            device=whisper_cfg["device"],
            remote_url=whisper_cfg.get("remote_url") or None,
            remote_timeout=whisper_cfg.get("remote_timeout", 30),
        )

        # LLM cleanup (optional)
        ollama_cfg = self.config["ollama"]
        self.cleanup = OllamaCleanup(
            base_url=ollama_cfg["base_url"],
            model=ollama_cfg["model"],
            timeout=ollama_cfg["timeout"],
        )

        # Text injection
        inject_cfg = self.config["injection"]
        self.injector = TextInjector(
            method=inject_cfg["method"],
            restore_clipboard=inject_cfg["restore_clipboard"],
        )

        # Text-to-Speech
        tts_cfg = self.config.get("tts", {})
        self.tts = TextToSpeech(
            hotkey=tts_cfg.get("hotkey", "ctrl+win+s"),
            rate=tts_cfg.get("rate", 175),
            volume=tts_cfg.get("volume", 1.0),
        )

        # Hotkey
        hotkey_cfg = self.config["hotkey"]
        self.hotkey = HotkeyListener(
            on_press=self._on_hotkey_press,
            on_release=self._on_hotkey_release,
            hotkey=hotkey_cfg["key"],
            mode=hotkey_cfg["mode"],
        )

        logger.info(f"Init complete in {time.perf_counter() - t0:.2f}s")

    # ── Config ────────────────────────────────────────────

    @staticmethod
    def _load_config(path: str) -> dict:
        # If config doesn't exist next to exe, copy the bundled default
        if not os.path.exists(path) and getattr(sys, "frozen", False):
            bundled = os.path.join(sys._MEIPASS, "config.yaml")
            if os.path.exists(bundled):
                import shutil
                shutil.copy2(bundled, path)
                logger.info(f"Copied default config to {path}")

        if not os.path.exists(path):
            logger.error(f"Config not found: {path}")
            sys.exit(1)
        with open(path) as f:
            return yaml.safe_load(f)

    # ── Listening control (single entry/exit points) ─────

    def _start_listening(self, source: str) -> None:
        if not self.is_running or self.is_listening or self._processing:
            return
        logger.info(f"[{source}] Capture started")
        self.is_listening = True
        self.island.set_state(IslandState.LISTENING)
        self._audio_ready.clear()
        self._recording_event.set()

    def _stop_and_process(self, source: str) -> None:
        if not self.is_running or not self.is_listening:
            return
        logger.info(f"[{source}] Capture stopped → processing")
        self._recording_event.clear()
        self.audio.is_recording = False
        self.is_listening = False
        self.island.set_audio_levels([0.0] * 5)  # Reset levels when stopping recording
        self.island.set_state(IslandState.TRANSCRIBING)
        threading.Thread(target=self._process_audio, daemon=True).start()

    def _on_island_click(self) -> None:
        if self.is_listening:
            self._stop_and_process("ISLAND")
        else:
            self._start_listening("ISLAND")

    def _on_hotkey_press(self) -> None:
        self._start_listening("HOTKEY")

    def _on_hotkey_release(self) -> None:
        self._stop_and_process("HOTKEY")

    # ── Recording loop (background thread) ───────────────

    def _recording_loop(self) -> None:
        while self.is_running:
            if self._recording_event.is_set():
                try:
                    audio_data = self.audio.record()
                    self._last_audio = audio_data
                    self._audio_ready.set()
                    self._recording_event.clear()
                except Exception as e:
                    logger.error(f"Recording error: {e}")
                    self._recording_event.clear()
                    self.island.set_state(IslandState.ERROR)
            elif self.is_listening:
                # While listening, update UI with current audio level
                rms = self.audio.current_rms
                # Map RMS to 5 EQ bar levels (0.0-1.0)
                # Use exponential scaling for better visual response
                level = min(1.0, rms * 50)  # Scale up RMS for visibility
                levels = [level * (0.6 + 0.4 * (i % 2)) for i in range(5)]
                self.island.set_audio_levels(levels)
                time.sleep(0.05)  # Update UI ~20x per second
            else:
                time.sleep(0.01)

    # ── Processing pipeline ──────────────────────────────

    def _process_audio(self) -> None:
        if not self._process_lock.acquire(blocking=False):
            logger.warning("Pipeline busy, skipping")
            return

        self._processing = True
        t_start = time.perf_counter()

        try:
            if not self._audio_ready.wait(timeout=10):
                logger.warning("Audio timeout")
                self.island.set_state(IslandState.IDLE)
                return

            audio = self._last_audio
            if audio is None or len(audio) == 0:
                self.island.set_state(IslandState.IDLE)
                return

            duration = len(audio) / self.config["audio"]["sample_rate"]
            logger.info(f"[PIPE] Audio: {duration:.1f}s ({len(audio)} samples)")

            # Transcribe
            t0 = time.perf_counter()
            raw_text = self.transcriber.transcribe(
                audio, sample_rate=self.config["audio"]["sample_rate"],
            )
            logger.info(f"[PIPE] Transcribe: {time.perf_counter() - t0:.2f}s → \"{raw_text}\"")

            if not raw_text:
                self.island.set_state(IslandState.IDLE)
                return

            # Optional LLM cleanup
            final_text = raw_text
            if self.config["ollama"]["enabled"]:
                t0 = time.perf_counter()
                final_text = self.cleanup.cleanup(raw_text)
                logger.info(f"[PIPE] Cleanup: {time.perf_counter() - t0:.2f}s → \"{final_text}\"")

            # Inject
            t0 = time.perf_counter()
            ok = self.injector.inject(final_text)
            logger.info(f"[PIPE] Inject: {time.perf_counter() - t0:.2f}s (ok={ok})")

            self.island.set_state(IslandState.IDLE)
            self.island.set_audio_levels([0.0] * 5)  # Reset levels on idle
            logger.info(f"[PIPE] Total: {time.perf_counter() - t_start:.2f}s")

        except Exception as e:
            logger.error(f"Pipeline error: {e}")
            self.island.set_state(IslandState.ERROR)
        finally:
            self._audio_ready.clear()
            self._processing = False
            self._process_lock.release()

    # ── Lifecycle ─────────────────────────────────────────

    def start(self) -> None:
        logger.info("Starting Wisper")
        self.is_running = True
        _hide_console()

        # Background recording thread
        threading.Thread(target=self._recording_loop, daemon=True).start()

        # Hotkey listener
        self.hotkey.start()

        # TTS listener
        self.tts.start()

        # Floating island (Qt — must be on main thread)
        self.island.start()
        self.island.set_state(IslandState.IDLE)

        hotkey_str = self.config["hotkey"]["key"]
        logger.info(f"Ready — press {hotkey_str} or click the island")

        # Qt event loop (blocks main thread)
        self.island.run_event_loop()

    def _pause(self) -> None:
        logger.info("Paused")
        self.is_running = False

    def _stop(self) -> None:
        logger.info("Stopping")
        self.is_running = False
        self.tts.stop()
        self.hotkey.stop()
        self.island.stop()
        sys.exit(0)


def main() -> None:
    default_cfg = str(_app_dir() / "config.yaml")
    config_path = sys.argv[1] if len(sys.argv) > 1 else default_cfg

    # First-run setup wizard (GUI — no terminal needed)
    from src.first_run import needs_setup, run_setup_wizard
    if needs_setup():
        from PyQt5.QtWidgets import QApplication
        qt_app = QApplication.instance() or QApplication(sys.argv)
        if not run_setup_wizard(qt_app):
            logger.error("Setup not completed")
            sys.exit(1)

    app = WisperApp(config_path)
    app.start()


if __name__ == "__main__":
    main()
