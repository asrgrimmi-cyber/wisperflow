"""Listening indicator overlay and system tray management."""

import logging
import threading
from enum import Enum
from typing import Optional, Callable
from PIL import Image, ImageDraw
import pystray

logger = logging.getLogger(__name__)


class IndicatorState(Enum):
    """State of the listening indicator."""

    IDLE = "idle"
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    ERROR = "error"


class ListeningIndicator:
    """Manages the listening indicator overlay."""

    def __init__(self, show_indicator: bool = True):
        """
        Initialize listening indicator.

        Args:
            show_indicator: Whether to show the indicator
        """
        self.show_indicator = show_indicator
        self.state = IndicatorState.IDLE

    def set_state(self, state: IndicatorState) -> None:
        """
        Set the indicator state.

        Args:
            state: New indicator state
        """
        self.state = state
        logger.debug(f"Indicator state: {state.value}")

        if self.show_indicator:
            self._update_display()

    def _update_display(self) -> None:
        """Update the visual display of the indicator."""
        # Placeholder for overlay implementation
        # In full implementation, this would show an on-screen indicator
        logger.debug(f"Indicator: {self.state.value}")


class TrayManager:
    """Manages system tray icon and menu."""

    def __init__(
        self,
        on_exit: Callable[[], None],
        on_pause: Callable[[], None],
        on_resume: Callable[[], None],
        tray_icon_enabled: bool = True,
    ):
        """
        Initialize tray manager.

        Args:
            on_exit: Callback for exit menu item
            on_pause: Callback for pause menu item
            on_resume: Callback for resume menu item
            tray_icon_enabled: Whether to show tray icon
        """
        self.on_exit = on_exit
        self.on_pause = on_pause
        self.on_resume = on_resume
        self.tray_icon_enabled = tray_icon_enabled
        self.is_running = True
        self.icon = None
        self.tray_thread = None
        self.state = IndicatorState.IDLE

    def _create_icon_image(self, state: IndicatorState) -> Image.Image:
        """
        Create a simple icon image based on state.

        Args:
            state: Current state

        Returns:
            PIL Image object
        """
        # Create a 64x64 image with a colored circle
        size = 64
        image = Image.new('RGB', (size, size), color='white')
        draw = ImageDraw.Draw(image)

        # Color based on state
        color_map = {
            IndicatorState.IDLE: '#808080',  # Gray
            IndicatorState.LISTENING: '#00FF00',  # Green
            IndicatorState.TRANSCRIBING: '#FFA500',  # Orange
            IndicatorState.ERROR: '#FF0000',  # Red
        }

        color = color_map.get(state, '#808080')
        margin = 8
        draw.ellipse(
            [margin, margin, size - margin, size - margin],
            fill=color,
            outline='black'
        )

        return image

    def _build_menu(self) -> pystray.Menu:
        """
        Build the tray icon context menu.

        Returns:
            pystray.Menu object
        """
        return pystray.Menu(
            pystray.MenuItem('Resume', self._on_resume, default=False),
            pystray.MenuItem('Pause', self._on_pause, default=False),
            pystray.MenuItem('Exit', self._on_exit, default=False),
        )

    def _on_pause(self, icon, item):
        """Handle pause menu item."""
        logger.info("Pause selected from tray")
        self.on_pause()

    def _on_resume(self, icon, item):
        """Handle resume menu item."""
        logger.info("Resume selected from tray")
        self.on_resume()

    def _on_exit(self, icon, item):
        """Handle exit menu item."""
        logger.info("Exit selected from tray")
        self.icon.stop()
        self.on_exit()

    def _run_tray(self) -> None:
        """Run the system tray icon (in a separate thread)."""
        try:
            image = self._create_icon_image(self.state)
            self.icon = pystray.Icon(
                'Whisper Dictation',
                image,
                menu=self._build_menu(),
            )
            self.icon.run()
        except Exception as e:
            logger.error(f"Error running tray icon: {e}")

    def start(self) -> None:
        """Start the tray manager."""
        if not self.tray_icon_enabled:
            logger.debug("Tray icon disabled")
            return

        logger.info("Starting system tray manager")
        self.tray_thread = threading.Thread(target=self._run_tray, daemon=True)
        self.tray_thread.start()

    def stop(self) -> None:
        """Stop the tray manager."""
        logger.info("Stopping system tray manager")
        self.is_running = False
        if self.icon:
            self.icon.stop()

    def set_state(self, state: IndicatorState) -> None:
        """
        Set the tray icon state.

        Args:
            state: New indicator state
        """
        self.state = state
        if self.icon:
            try:
                image = self._create_icon_image(state)
                self.icon.icon = image
            except Exception as e:
                logger.debug(f"Could not update tray icon: {e}")
        logger.debug(f"Tray state: {state.value}")
