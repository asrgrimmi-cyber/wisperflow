"""Text injection into the currently focused window."""

import logging
import pyperclip
import time
import keyboard as kb
from typing import Optional

logger = logging.getLogger(__name__)


class TextInjector:
    """Injects text into the currently focused window."""

    def __init__(self, method: str = "clipboard", restore_clipboard: bool = True):
        """
        Initialize text injector.

        Args:
            method: "clipboard" (preferred) or "keystroke"
            restore_clipboard: Whether to restore the previous clipboard contents
        """
        self.method = method
        self.restore_clipboard = restore_clipboard

    def inject(self, text: str) -> bool:
        """
        Inject text into the focused window.

        Args:
            text: Text to inject

        Returns:
            True if successful, False otherwise
        """
        if not text:
            logger.warning("Empty text, skipping injection")
            return False

        try:
            if self.method == "clipboard":
                return self._inject_clipboard(text)
            elif self.method == "keystroke":
                return self._inject_keystroke(text)
            else:
                logger.error(f"Unknown injection method: {self.method}")
                return False
        except Exception as e:
            logger.error(f"Error injecting text: {e}")
            return False

    def _inject_clipboard(self, text: str) -> bool:
        """
        Inject text using clipboard paste.

        Args:
            text: Text to inject

        Returns:
            True if successful
        """
        try:
            # Save current clipboard content
            previous_clipboard = ""
            if self.restore_clipboard:
                try:
                    previous_clipboard = pyperclip.paste()
                except Exception as e:
                    logger.debug(f"Could not read clipboard: {e}")

            # Copy text to clipboard
            pyperclip.copy(text)
            logger.debug("Text copied to clipboard")

            # Small delay to ensure clipboard is ready
            time.sleep(0.1)

            # Send Ctrl+V to paste using keyboard library
            kb.press('ctrl')
            kb.press('v')
            kb.release('v')
            kb.release('ctrl')
            logger.debug("Pasted from clipboard")

            # Restore previous clipboard content
            if self.restore_clipboard and previous_clipboard:
                time.sleep(0.2)  # Wait for paste to complete
                try:
                    pyperclip.copy(previous_clipboard)
                    logger.debug("Restored previous clipboard content")
                except Exception as e:
                    logger.debug(f"Could not restore clipboard: {e}")

            return True

        except Exception as e:
            logger.error(f"Clipboard injection failed: {e}")
            return False

    def _inject_keystroke(self, text: str) -> bool:
        """
        Inject text using simulated keystrokes.

        Args:
            text: Text to inject

        Returns:
            True if successful
        """
        try:
            # Use clipboard as fallback for special characters
            if not all(ord(c) < 128 for c in text):
                logger.debug("Text contains non-ASCII characters, using clipboard method")
                return self._inject_clipboard(text)

            # Type the text using keyboard library
            kb.write(text, interval=0.01)
            logger.debug("Text injected via keystrokes")
            return True

        except Exception as e:
            logger.error(f"Keystroke injection failed: {e}")
            return False
