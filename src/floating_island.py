"""Floating island UI — PyQt5 with true per-pixel alpha (WS_EX_LAYERED).

No color-key hack. Clean anti-aliased edges on any background.
Uses QPainter for all rendering — vector-quality at any DPI.

Layout:
  IDLE (minimized):  Small circle with centered mic icon (green)
  LISTENING:         Expanded pill: [mic (blue)] [5 EQ bars]
  TRANSCRIBING:      Expanded pill: [mic (amber)] [spinner]
  ERROR:             Expanded pill: [mic (red)] [Error label]
"""

import logging
import math
import sys
import threading
from enum import Enum
from typing import Callable, Optional

from PyQt5.QtCore import (
    Qt, QTimer, QRectF, QPointF, QSize, pyqtSignal, QObject,
)
from PyQt5.QtGui import (
    QPainter, QPainterPath, QColor, QPen, QFont, QFontDatabase,
    QBrush, QLinearGradient,
)
from PyQt5.QtWidgets import QApplication, QWidget

logger = logging.getLogger(__name__)


class IslandState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    TRANSCRIBING = "transcribing"
    ERROR = "error"


# ── Design tokens ─────────────────────────────────────────
PILL_W_FULL = 100
PILL_W_MINI = 30
PILL_H = 30
TRANSITION_FRAMES = 12   # ~0.4s at 30fps

_INK       = QColor(231, 233, 238)
_ACCENT_GR = QColor(108, 114, 126)    # Gray for IDLE state (neutral)
_ACCENT_BL = QColor(47, 129, 247)
_ACCENT_AM = QColor(245, 166, 35)
_RED       = QColor(235, 87, 87)

STYLES = {
    IslandState.IDLE: {
        "pill_bg":  QColor(25, 28, 32, 245),
        "border":   _ACCENT_GR,
        "icon":     _ACCENT_GR,
        "content":  "none",
    },
    IslandState.LISTENING: {
        "pill_bg":  QColor(22, 30, 43, 245),
        "border":   _ACCENT_BL,
        "icon":     _ACCENT_BL,
        "content":  "wave",
    },
    IslandState.TRANSCRIBING: {
        "pill_bg":  QColor(36, 29, 18, 245),
        "border":   _ACCENT_AM,
        "icon":     _ACCENT_AM,
        "content":  "spin",
    },
    IslandState.ERROR: {
        "pill_bg":  QColor(40, 20, 20, 245),
        "border":   _RED,
        "icon":     _RED,
        "content":  "label",
        "label":    "Error",
    },
}


def _ease_out_cubic(t: float) -> float:
    return 1.0 - (1.0 - t) ** 3


class _StateSignal(QObject):
    """Bridge to send state changes from any thread to the Qt thread."""
    changed = pyqtSignal(str)


class IslandWidget(QWidget):
    """The actual Qt widget — frameless, translucent, always-on-top."""

    def __init__(self, on_click, on_right_click=None, on_exit=None):
        super().__init__()
        self._on_click = on_click
        self._on_right_click = on_right_click
        self._on_exit = on_exit

        self.state = IslandState.IDLE
        self._anim_tick = 0
        self._current_width = float(PILL_W_MINI)
        self._target_width = float(PILL_W_MINI)
        self._transition_frame = 0
        self._transition_from = float(PILL_W_MINI)
        self._drag_origin = None
        self._audio_levels = [0.0] * 5  # Real-time audio levels for 5 EQ bars

        # Window flags: frameless, on top, tool window (no taskbar entry)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.WindowStaysOnTopHint
            | Qt.Tool
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setAttribute(Qt.WA_ShowWithoutActivating)

        # Fixed height, max width for canvas
        canvas_w = PILL_W_FULL + 12
        canvas_h = PILL_H + 12
        self.setFixedSize(canvas_w, canvas_h)

        # Position bottom-center
        screen = QApplication.primaryScreen().geometry()
        x = (screen.width() - canvas_w) // 2
        y = screen.height() - canvas_h - 55
        self.move(x, y)

        # Animation timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._on_tick)

        # Font
        self._font = QFont("Segoe UI", 10)
        self._font.setWeight(QFont.Medium)

    def set_state(self, state: IslandState) -> None:
        self.state = state
        new_target = float(PILL_W_MINI if state == IslandState.IDLE else PILL_W_FULL)
        if new_target != self._target_width:
            self._transition_from = self._current_width
            self._target_width = new_target
            self._transition_frame = 0

        is_animated = state in (IslandState.LISTENING, IslandState.TRANSCRIBING)
        transitioning = self._current_width != self._target_width
        if is_animated or transitioning:
            if not self._timer.isActive():
                self._timer.start(33)  # ~30fps
        self.update()

    def set_audio_levels(self, levels: list) -> None:
        """Update audio levels for EQ bar visualization.

        Args:
            levels: List of 5 float values (0.0-1.0) for each bar height
        """
        if len(levels) >= 5:
            self._audio_levels = levels[:5]
        else:
            self._audio_levels = list(levels) + [0.0] * (5 - len(levels))

    def _on_tick(self) -> None:
        self._anim_tick += 1

        # Update transition
        if self._current_width != self._target_width:
            self._transition_frame += 1
            t = min(1.0, self._transition_frame / TRANSITION_FRAMES)
            t = _ease_out_cubic(t)
            self._current_width = self._transition_from + (self._target_width - self._transition_from) * t
            if t >= 1.0:
                self._current_width = self._target_width

        is_animated = self.state in (IslandState.LISTENING, IslandState.TRANSCRIBING)
        transitioning = self._current_width != self._target_width
        if not is_animated and not transitioning:
            self._timer.stop()
            self._anim_tick = 0

        self.update()

    # ── Painting ──────────────────────────────────────────

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)

        style = STYLES[self.state]
        pw = self._current_width
        ph = PILL_H
        cr = ph / 2.0

        # Center pill in widget
        cx = self.width() / 2.0
        cy = self.height() / 2.0
        pill_rect = QRectF(cx - pw / 2, cy - ph / 2, pw, ph)

        # Pill background
        path = QPainterPath()
        path.addRoundedRect(pill_rect, cr, cr)
        p.fillPath(path, QBrush(style["pill_bg"]))

        # Border
        pen = QPen(style["border"], 1.0)
        p.setPen(pen)
        p.drawRoundedRect(pill_rect, cr, cr)

        # Expand ratio for content
        expand = (self._current_width - PILL_W_MINI) / max(1, PILL_W_FULL - PILL_W_MINI)
        expand = max(0.0, min(1.0, expand))

        # Mic icon position: centered when mini, left-aligned when expanded
        icon_cx_center = cx
        icon_cx_left = pill_rect.left() + 19
        icon_cx = icon_cx_center + (icon_cx_left - icon_cx_center) * expand
        icon_cy = cy
        icon_scale = 0.75 + 0.25 * expand

        self._draw_mic(p, icon_cx, icon_cy, style["icon"], icon_scale)

        # Content (fades in during expansion)
        if expand > 0.3:
            content_alpha = min(1.0, (expand - 0.3) / 0.5)
            content_left = pill_rect.left() + 36
            content_right = pill_rect.right() - 10

            if style["content"] == "wave":
                self._draw_eq_bars(p, content_left, content_right, cy, content_alpha)
            elif style["content"] == "spin":
                self._draw_spinner(p, content_left, content_right, cy, content_alpha)
            elif style["content"] == "label":
                label = style.get("label", "")
                color = QColor(style["icon"])
                color.setAlphaF(content_alpha)
                p.setPen(QPen(color))
                p.setFont(self._font)
                text_rect = QRectF(content_left, pill_rect.top(), content_right - content_left, ph)
                p.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, label)

        p.end()

    def _draw_mic(self, p: QPainter, cx, cy, color, scale):
        """Lucide mic icon via QPainterPath — true vector, no raster."""
        p.save()
        p.translate(cx, cy)
        p.scale(scale, scale)

        u = 16.0 / 24.0  # 16px icon on 24-unit grid

        pen = QPen(color, 1.7)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)
        p.setBrush(Qt.NoBrush)

        # Capsule: rounded rect (9,2)→(15,12) in SVG coords, centered at (12,12)
        def sx(xv): return (xv - 12) * u
        def sy(yv): return (yv - 12) * u

        cap = QRectF(sx(9), sy(2), 6 * u, 10 * u)
        p.drawRoundedRect(cap, 3 * u, 3 * u)

        # Cradle arc
        arc_rect = QRectF(sx(5), sy(3), 14 * u, 14 * u)
        p.drawArc(arc_rect, 180 * 16, 180 * 16)  # bottom half

        # Stand line
        p.drawLine(QPointF(sx(12), sy(19)), QPointF(sx(12), sy(22)))

        p.restore()

    def _draw_eq_bars(self, p: QPainter, left, right, cy, alpha):
        """5 equalizer bars — real audio levels or animation fallback."""
        bar_w = 3.0
        gap = 3.0
        count = 5
        total = count * bar_w + (count - 1) * gap
        start_x = left + (right - left - total) / 2

        color = QColor(_ACCENT_BL)
        color.setAlphaF(alpha)
        p.setPen(Qt.NoPen)

        # Check if we have real audio levels (any non-zero)
        has_real_levels = any(lvl > 0.01 for lvl in self._audio_levels)

        for i in range(count):
            if has_real_levels:
                # Use real audio levels (0.0-1.0 scale, max height 17)
                h = 5 + self._audio_levels[i] * (17 - 5)
            else:
                # Fallback to animation when no audio input
                delay = i * 0.15
                t = (self._anim_tick * 0.033 + delay) * 2 * math.pi
                h = 5 + (17 - 5) * (0.5 + 0.5 * math.sin(t))

            x = start_x + i * (bar_w + gap)
            rect = QRectF(x, cy - h / 2, bar_w, h)
            path = QPainterPath()
            path.addRoundedRect(rect, bar_w / 2, bar_w / 2)
            p.fillPath(path, QBrush(color))

    def _draw_spinner(self, p: QPainter, left, right, cy, alpha):
        """Spinning arc matching CSS spec."""
        r = 8.0
        spin_cx = left + (right - left) / 2
        spin_cy = cy

        color = QColor(_ACCENT_AM)
        color.setAlphaF(alpha)
        pen = QPen(color, 2.0)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)

        angle = (self._anim_tick * (360 / 21)) % 360
        arc_rect = QRectF(spin_cx - r, spin_cy - r, 2 * r, 2 * r)
        p.drawArc(arc_rect, int(-angle * 16), int(-120 * 16))

    # ── Mouse events ─────────────────────────────────────

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._drag_origin = event.globalPos() - self.pos()
            self._drag_moved = False
        elif event.button() == Qt.RightButton:
            self._show_context_menu(event.globalPos())

    def mouseMoveEvent(self, event):
        if self._drag_origin and event.buttons() & Qt.LeftButton:
            delta = event.globalPos() - self._drag_origin - self.pos()
            if abs(delta.x()) > 3 or abs(delta.y()) > 3:
                self._drag_moved = True
            self.move(event.globalPos() - self._drag_origin)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            if not getattr(self, '_drag_moved', False):
                if self._on_click:
                    self._on_click()
            self._drag_origin = None

    def _show_context_menu(self, pos):
        from PyQt5.QtWidgets import QMenu, QAction
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background: #1c1f24; color: #e7e9ee;
                border: 1px solid #2e333b; border-radius: 6px;
                padding: 4px;
            }
            QMenu::item { padding: 6px 20px; border-radius: 4px; }
            QMenu::item:selected { background: #2e333b; }
            QMenu::separator { height: 1px; background: #2e333b; margin: 4px 8px; }
        """)
        pause_action = menu.addAction("Pause")
        menu.addSeparator()
        exit_action = menu.addAction("Exit")

        action = menu.exec_(pos)
        if action == pause_action and self._on_right_click:
            self._on_right_click()
        elif action == exit_action:
            if self._on_exit:
                self._on_exit()
            self.close()


class FloatingIsland:
    """Wrapper for the Qt island widget.

    Qt requires QApplication on the main thread. Call start_blocking() from main,
    or start() which creates QApplication on the calling thread.
    """

    def __init__(
        self,
        on_click: Callable[[], None],
        on_right_click: Optional[Callable[[], None]] = None,
        on_exit: Optional[Callable[[], None]] = None,
    ):
        self.on_click = on_click
        self.on_right_click = on_right_click
        self.on_exit = on_exit
        self.state = IslandState.IDLE
        self._widget: Optional[IslandWidget] = None
        self._app: Optional[QApplication] = None
        self._signal = _StateSignal()
        self._ready = threading.Event()

    def start(self) -> None:
        """Initialize and show the island. Call from main thread.
        Non-blocking — starts the Qt event loop via processEvents timer."""
        self._app = QApplication.instance() or QApplication(sys.argv)
        self._app.setQuitOnLastWindowClosed(False)

        self._widget = IslandWidget(
            on_click=self.on_click,
            on_right_click=self.on_right_click,
            on_exit=self.on_exit,
        )

        def _on_state_changed(state_str):
            state = IslandState(state_str)
            self._widget.set_state(state)

        self._signal.changed.connect(_on_state_changed, Qt.QueuedConnection)
        self._widget.show()
        self._ready.set()

    def run_event_loop(self) -> None:
        """Run the Qt event loop (blocks). Call from main thread."""
        if self._app:
            self._app.exec_()

    def process_events(self) -> None:
        """Process pending Qt events. Call periodically from main loop."""
        if self._app:
            self._app.processEvents()

    def stop(self) -> None:
        if self._app:
            try:
                self._app.quit()
            except Exception:
                pass

    def set_state(self, state: IslandState) -> None:
        self.state = state
        try:
            self._signal.changed.emit(state.value)
        except Exception:
            pass

    def set_audio_levels(self, levels: list) -> None:
        """Update audio levels on the widget."""
        if self._widget:
            self._widget.set_audio_levels(levels)
