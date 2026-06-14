"""Global hotkey listener for the speech-to-text tool."""

import logging
from pynput import keyboard
from typing import Callable, Optional

logger = logging.getLogger(__name__)


class HotkeyListener:
    """Listens for global hotkey (Ctrl+Win) to toggle recording."""

    def __init__(
        self,
        on_press: Callable[[], None],
        on_release: Callable[[], None],
        hotkey: str = "ctrl+win",
        mode: str = "hold",
    ):
        """
        Initialize the hotkey listener.

        Args:
            on_press: Callback when hotkey is pressed
            on_release: Callback when hotkey is released
            hotkey: Hotkey string (e.g., "ctrl+win")
            mode: "hold" (press & hold) or "toggle" (press to start/stop)
        """
        self.on_press = on_press
        self.on_release = on_release
        self.hotkey = hotkey
        self.mode = mode
        self.listener: Optional[keyboard.Listener] = None
        self.is_combination_pressed = False
        self.is_active = False
        self.pressed_keys = set()

        # Parse hotkey
        self.key_combination = self._parse_hotkey(hotkey)

    def _parse_hotkey(self, hotkey: str) -> set:
        """
        Parse hotkey string to a set of keys.

        Args:
            hotkey: Hotkey string (e.g., "ctrl+win")

        Returns:
            Set of keyboard.Key objects
        """
        keys = set()
        parts = hotkey.lower().split("+")

        key_map = {
            "ctrl": keyboard.Key.ctrl,
            "shift": keyboard.Key.shift,
            "alt": keyboard.Key.alt,
            "win": keyboard.Key.cmd,
        }

        for part in parts:
            part = part.strip()
            if part in key_map:
                keys.add(key_map[part])

        return keys

    def on_key_press(self, key: keyboard.Key) -> None:
        """Handle key press event."""
        try:
            if key in self.key_combination:
                self.pressed_keys.add(key)

                # Check if all keys in the combination are now pressed
                if self.key_combination.issubset(self.pressed_keys):
                    if not self.is_combination_pressed:
                        self.is_combination_pressed = True
                        logger.debug(f"Hotkey combination pressed: {self.hotkey}")

                        if self.mode == "hold":
                            self.on_press()
                        elif self.mode == "toggle" and not self.is_active:
                            self.on_press()
                            self.is_active = True
        except Exception as e:
            logger.error(f"Error in on_key_press: {e}")

    def on_key_release(self, key: keyboard.Key) -> None:
        """Handle key release event."""
        try:
            if key in self.key_combination:
                self.pressed_keys.discard(key)

                # If any key in the combination was released
                if not self.key_combination.issubset(self.pressed_keys):
                    if self.is_combination_pressed:
                        self.is_combination_pressed = False
                        logger.debug(f"Hotkey combination released: {self.hotkey}")

                        if self.mode == "hold":
                            self.on_release()
                        elif self.mode == "toggle" and self.is_active:
                            self.on_release()
                            self.is_active = False
        except Exception as e:
            logger.error(f"Error in on_key_release: {e}")

    def start(self) -> None:
        """Start listening for global hotkey."""
        logger.info(f"Starting hotkey listener ({self.hotkey}, mode={self.mode})")
        self.listener = keyboard.Listener(
            on_press=self.on_key_press, on_release=self.on_key_release
        )
        self.listener.start()

    def stop(self) -> None:
        """Stop listening for global hotkey."""
        logger.info("Stopping hotkey listener")
        if self.listener:
            self.listener.stop()
            self.listener.join()
            self.listener = None
