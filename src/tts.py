"""Text-to-Speech module — select text, press hotkey, hear it spoken.

Uses Microsoft Edge neural voices via edge-tts for natural-sounding speech.
"""

import asyncio
import io
import logging
import tempfile
import threading
import time
from pathlib import Path

import keyboard
import pyperclip

logger = logging.getLogger("wisper.tts")


class TextToSpeech:
    """Reads selected text aloud using Microsoft Edge neural TTS voices."""

    def __init__(
        self,
        hotkey: str = "ctrl+win+r",
        voice: str = "en-US-GuyNeural",
        rate: str = "+0%",
        volume: str = "+0%",
        on_speak_start=None,
        on_speak_end=None,
    ):
        self.hotkey = hotkey
        self.voice = voice
        self.rate = rate
        self.volume = volume
        self._speaking = False
        self._stop_flag = False
        self._lock = threading.Lock()
        self.on_speak_start = on_speak_start
        self.on_speak_end = on_speak_end

    def start(self) -> None:
        """Register the TTS hotkey."""
        keyboard.add_hotkey(self.hotkey, self._on_hotkey, suppress=True)
        logger.info(f"TTS ready — press {self.hotkey} to read selected text")

    def stop(self) -> None:
        """Unregister the hotkey and stop any ongoing speech."""
        try:
            keyboard.remove_hotkey(self.hotkey)
        except (KeyError, ValueError):
            pass
        self._stop_flag = True

    def _on_hotkey(self) -> None:
        if self._speaking:
            self._stop_flag = True
            return
        threading.Thread(target=self._speak_selected, daemon=True).start()

    def _speak_selected(self) -> None:
        with self._lock:
            self._speaking = True
            self._stop_flag = False

            try:
                # Save clipboard
                old_clip = ""
                try:
                    old_clip = pyperclip.paste()
                except Exception:
                    pass

                pyperclip.copy("")
                # Wait for hotkey modifiers to release
                time.sleep(0.5)
                for key in ("ctrl", "win", "shift", "alt"):
                    try:
                        keyboard.release(key)
                    except Exception:
                        pass
                time.sleep(0.1)
                keyboard.press_and_release("ctrl+c")
                time.sleep(0.3)

                text = pyperclip.paste().strip()

                # Restore clipboard
                try:
                    pyperclip.copy(old_clip)
                except Exception:
                    pass

                if not text:
                    logger.info("TTS: no text selected")
                    return

                logger.info(f"TTS: speaking {len(text)} chars with voice={self.voice}")
                self._speak_edge(text)

            except Exception as e:
                logger.error(f"TTS error: {e}", exc_info=True)
            finally:
                self._speaking = False

    def _speak_edge(self, text: str) -> None:
        """Generate speech with edge-tts and play via sounddevice."""
        try:
            import edge_tts
            import numpy as np
            import sounddevice as sd
            import soundfile as sf

            # Generate audio to a temp file
            tmp = Path(tempfile.gettempdir()) / "wisper_tts.mp3"

            async def _generate():
                communicate = edge_tts.Communicate(
                    text, self.voice, rate=self.rate, volume=self.volume
                )
                await communicate.save(str(tmp))

            asyncio.run(_generate())

            if self._stop_flag:
                return

            # Read and play
            data, samplerate = sf.read(str(tmp), dtype="float32")
            if self._stop_flag:
                return

            logger.info(f"TTS: playing {len(data)/samplerate:.1f}s audio")

            # Notify that speech is starting
            if self.on_speak_start:
                try:
                    self.on_speak_start()
                except Exception as e:
                    logger.error(f"on_speak_start callback error: {e}")

            sd.play(data, samplerate)

            # Wait for playback, checking stop flag
            while sd.get_stream().active:
                if self._stop_flag:
                    sd.stop()
                    logger.info("TTS: stopped by user")
                    if self.on_speak_end:
                        try:
                            self.on_speak_end()
                        except Exception as e:
                            logger.error(f"on_speak_end callback error: {e}")
                    return
                time.sleep(0.1)

            sd.wait()

            # Notify that speech has ended
            if self.on_speak_end:
                try:
                    self.on_speak_end()
                except Exception as e:
                    logger.error(f"on_speak_end callback error: {e}")

        except ImportError:
            logger.warning("edge-tts not available, falling back to pyttsx3")
            self._speak_pyttsx3(text)
        except Exception as e:
            logger.error(f"edge-tts error: {e}, falling back to pyttsx3")
            self._speak_pyttsx3(text)
        finally:
            # Cleanup temp file
            try:
                tmp = Path(tempfile.gettempdir()) / "wisper_tts.mp3"
                tmp.unlink(missing_ok=True)
            except Exception:
                pass

    def _speak_pyttsx3(self, text: str) -> None:
        """Fallback: speak using Windows SAPI via pyttsx3."""
        try:
            import pyttsx3

            if self.on_speak_start:
                try:
                    self.on_speak_start()
                except Exception as e:
                    logger.error(f"on_speak_start callback error: {e}")

            engine = pyttsx3.init()
            engine.setProperty("rate", 175)
            engine.setProperty("volume", 1.0)
            engine.say(text)
            engine.runAndWait()
            engine.stop()

            if self.on_speak_end:
                try:
                    self.on_speak_end()
                except Exception as e:
                    logger.error(f"on_speak_end callback error: {e}")
        except Exception as e:
            logger.error(f"pyttsx3 fallback error: {e}")
            if self.on_speak_end:
                try:
                    self.on_speak_end()
                except Exception as e:
                    logger.error(f"on_speak_end callback error: {e}")
