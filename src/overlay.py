"""Listening indicator overlay and system tray management."""

import logging
from enum import Enum
from typing import Optional, Callable

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

    def start(self) -> None:
        """Start the tray manager."""
        if not self.tray_icon_enabled:
            logger.debug("Tray icon disabled")
            return

        logger.info("Starting system tray manager")
        # Placeholder for pystray implementation
        # In full implementation, this would set up the tray icon with menu

    def stop(self) -> None:
        """Stop the tray manager."""
        logger.info("Stopping system tray manager")
        self.is_running = False

    def set_state(self, state: IndicatorState) -> None:
        """
        Set the tray icon state.

        Args:
            state: New indicator state
        """
        # Update tray icon color/animation based on state
        logger.debug(f"Tray state: {state.value}")
