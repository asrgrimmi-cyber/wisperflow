"""Global hotkey listener for the speech-to-text tool."""

import logging
import keyboard
from typing import Callable

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
            mode: "hold" (press & hold to talk) or "toggle" (press once to start/stop)
        """
        self.on_press = on_press
        self.on_release = on_release
        self.hotkey = hotkey
        self.mode = mode
        self.is_combination_pressed = False
        self.is_active = False

    def on_hotkey(self) -> None:
        """Handle hotkey press/release."""
        if self.mode == "hold":
            # For hold mode, we need to detect press and release separately
            # This will be called on press
            if not self.is_combination_pressed:
                self.is_combination_pressed = True
                logger.debug(f"Hotkey pressed: {self.hotkey}")
                self.on_press()

    def start(self) -> None:
        """Start listening for global hotkey."""
        logger.info(f"Starting hotkey listener ({self.hotkey}, mode={self.mode})")

        if self.mode == "hold":
            # For hold mode, detect when the combination is pressed and released
            def on_combo():
                if not self.is_combination_pressed:
                    self.is_combination_pressed = True
                    logger.debug(f"Hotkey pressed: {self.hotkey}")
                    self.on_press()

            keyboard.add_hotkey(self.hotkey, on_combo)

            # Add release handler
            def on_release_handler():
                if self.is_combination_pressed:
                    self.is_combination_pressed = False
                    logger.debug(f"Hotkey released: {self.hotkey}")
                    self.on_release()

            # Get the modifier keys from the hotkey string
            parts = [p.strip().lower() for p in self.hotkey.split('+')]
            modifiers = [p for p in parts if p in ['ctrl', 'shift', 'alt', 'win']]

            # Register release handlers for modifier keys
            for modifier in modifiers:
                key_names = {
                    'ctrl': ['left ctrl', 'right ctrl'],
                    'shift': ['left shift', 'right shift'],
                    'alt': ['left alt', 'right alt'],
                    'win': ['left windows', 'right windows']
                }
                for key_name in key_names.get(modifier, []):
                    keyboard.add_hotkey(key_name, on_release_handler, trigger_on_release=True)

        elif self.mode == "toggle":
            # For toggle mode, press to start, press again to stop
            def on_combo():
                if not self.is_active:
                    self.is_active = True
                    logger.debug(f"Hotkey pressed: {self.hotkey} (toggle on)")
                    self.on_press()
                else:
                    self.is_active = False
                    logger.debug(f"Hotkey pressed: {self.hotkey} (toggle off)")
                    self.on_release()

            keyboard.add_hotkey(self.hotkey, on_combo)

    def stop(self) -> None:
        """Stop listening for global hotkey."""
        logger.info("Stopping hotkey listener")
        keyboard.remove_all_hotkeys()
