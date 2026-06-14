"""Main entry point for the speech-to-text dictation tool."""

import logging
import yaml
import sys
import os
import time
import threading
from pathlib import Path
from typing import Optional

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.hotkey import HotkeyListener
from src.audio import AudioCapture
from src.transcribe import WhisperTranscriber
from src.cleanup import OllamaCleanup
from src.inject import TextInjector
from src.overlay import ListeningIndicator, TrayManager, IndicatorState

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class SpeechToTextApp:
    """Main application class orchestrating the speech-to-text pipeline."""

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize the speech-to-text application.

        Args:
            config_path: Path to configuration file
        """
        self.config = self._load_config(config_path)
        self.is_running = False
        self.is_listening = False
        self.recording_event = threading.Event()
        self.audio_ready_event = threading.Event()
        self.last_audio_data = None

        logger.info("Initializing Speech-to-Text Dictation Tool")

        # Initialize components
        self.audio_capture = AudioCapture(
            sample_rate=self.config["audio"]["sample_rate"],
            channels=self.config["audio"]["channels"],
            silence_threshold=self.config["audio"]["silence_threshold"],
            silence_duration=self.config["audio"]["silence_duration"],
        )

        self.transcriber = WhisperTranscriber(
            model_path=self.config["whisper"]["model_path"],
            model_name=self.config["whisper"]["model_name"],
            language=self.config["whisper"]["language"],
            device=self.config["whisper"]["device"],
        )

        self.cleanup = OllamaCleanup(
            base_url=self.config["ollama"]["base_url"],
            model=self.config["ollama"]["model"],
            timeout=self.config["ollama"]["timeout"],
        )

        self.text_injector = TextInjector(
            method=self.config["injection"]["method"],
            restore_clipboard=self.config["injection"]["restore_clipboard"],
        )

        self.indicator = ListeningIndicator(
            show_indicator=self.config["ui"]["show_indicator"]
        )

        self.tray_manager = TrayManager(
            on_exit=self.stop,
            on_pause=self.pause,
            on_resume=self.resume,
            tray_icon_enabled=self.config["ui"]["tray_icon_enabled"],
        )

        self.hotkey_listener = HotkeyListener(
            on_press=self.on_hotkey_press,
            on_release=self.on_hotkey_release,
            hotkey=self.config["hotkey"]["key"],
            mode=self.config["hotkey"]["mode"],
        )

    def _load_config(self, config_path: str) -> dict:
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to configuration file

        Returns:
            Configuration dictionary
        """
        if not os.path.exists(config_path):
            logger.error(f"Configuration file not found: {config_path}")
            sys.exit(1)

        with open(config_path, "r") as f:
            config = yaml.safe_load(f)

        logger.info(f"Configuration loaded from {config_path}")
        return config

    def on_hotkey_press(self) -> None:
        """Called when hotkey is pressed."""
        if self.is_running and not self.is_listening:
            logger.info("Hotkey pressed, starting capture")
            self.is_listening = True
            self.indicator.set_state(IndicatorState.LISTENING)
            self.audio_ready_event.clear()
            self.recording_event.set()

    def on_hotkey_release(self) -> None:
        """Called when hotkey is released."""
        if self.is_running and self.is_listening:
            logger.info("Hotkey released, stopping capture")
            self.recording_event.clear()
            self.is_listening = False
            # Process the audio in a background thread to avoid blocking hotkey handler
            thread = threading.Thread(target=self._process_audio)
            thread.daemon = True
            thread.start()

    def _recording_loop(self) -> None:
        """Background thread that handles audio recording."""
        while self.is_running:
            # Wait until recording is requested
            if self.recording_event.is_set():
                try:
                    logger.debug("Recording thread: waiting for audio")
                    audio_data = self.audio_capture.record()
                    self.last_audio_data = audio_data
                    self.audio_ready_event.set()
                    logger.debug(f"Recording thread: got {len(audio_data)} samples")
                except Exception as e:
                    logger.error(f"Recording thread error: {e}")
                    self.indicator.set_state(IndicatorState.ERROR)
            else:
                time.sleep(0.01)

    def _process_audio(self) -> None:
        """Process recorded audio and inject text."""
        try:
            # Wait for audio to be ready (with timeout)
            if not self.audio_ready_event.wait(timeout=10):
                logger.warning("Audio recording timed out")
                self.indicator.set_state(IndicatorState.IDLE)
                return

            audio_data = self.last_audio_data

            if audio_data is None or len(audio_data) == 0:
                logger.warning("No audio recorded")
                self.indicator.set_state(IndicatorState.IDLE)
                return

            self.indicator.set_state(IndicatorState.TRANSCRIBING)

            # Transcribe
            raw_text = self.transcriber.transcribe(
                audio_data,
                sample_rate=self.config["audio"]["sample_rate"],
            )

            if not raw_text:
                logger.warning("Transcription failed")
                self.indicator.set_state(IndicatorState.IDLE)
                return

            # Cleanup if enabled
            final_text = raw_text
            if self.config["ollama"]["enabled"]:
                logger.info("Running LLM cleanup")
                final_text = self.cleanup.cleanup(raw_text)

            # Inject text
            logger.info(f"Injecting text: {final_text}")
            success = self.text_injector.inject(final_text)

            if success:
                logger.info("Text injected successfully")
            else:
                logger.error("Text injection failed")

            self.indicator.set_state(IndicatorState.IDLE)

        except Exception as e:
            logger.error(f"Error processing audio: {e}")
            self.indicator.set_state(IndicatorState.ERROR)
        finally:
            self.audio_ready_event.clear()

    def pause(self) -> None:
        """Pause the application."""
        logger.info("Application paused")
        self.is_running = False

    def resume(self) -> None:
        """Resume the application."""
        logger.info("Application resumed")
        self.is_running = True

    def start(self) -> None:
        """Start the application."""
        logger.info("Starting application")
        self.is_running = True

        try:
            # Start background recording thread
            recording_thread = threading.Thread(target=self._recording_loop)
            recording_thread.daemon = True
            recording_thread.start()

            # Start hotkey listener
            self.hotkey_listener.start()
            self.tray_manager.start()
            self.indicator.set_state(IndicatorState.IDLE)

            logger.info("Application ready, waiting for hotkey...")
            logger.info(f"Press {self.config['hotkey']['key']} to start dictating")

            # Keep the application running
            while self.is_running:
                time.sleep(0.1)

        except KeyboardInterrupt:
            logger.info("Keyboard interrupt, shutting down")
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the application."""
        logger.info("Stopping application")
        self.is_running = False

        self.hotkey_listener.stop()
        self.tray_manager.stop()

        logger.info("Application stopped")
        sys.exit(0)


def main() -> None:
    """Main entry point."""
    # Get config path from command line or use default
    config_path = "config.yaml"
    if len(sys.argv) > 1:
        config_path = sys.argv[1]

    app = SpeechToTextApp(config_path)
    app.start()


if __name__ == "__main__":
    main()
