"""Animated status bubble overlay for WhisperWriter.

A modern, pill-shaped overlay that appears at the bottom-center of the screen
with animated sound bars during recording and a spinner during transcription.
"""

import math
import sys
import os
from PyQt5.QtCore import (
    Qt, pyqtSignal, pyqtSlot, QTimer, QPropertyAnimation, QEasingCurve,
    QRectF, pyqtProperty, QSize
)
from PyQt5.QtGui import (
    QPainter, QColor, QBrush, QPen, QPainterPath, QFont, QFontMetrics,
    QLinearGradient, QGuiApplication
)
from PyQt5.QtWidgets import QApplication, QWidget

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from ui.theme import (
    FONT_FAMILY,
    BUBBLE_BG, BUBBLE_TEXT,
    BUBBLE_ACCENT_RECORDING, BUBBLE_ACCENT_TRANSCRIBING,
    BUBBLE_ACCENT_PROCESSING, BUBBLE_ACCENT_DONE,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

BUBBLE_WIDTH = 220
BUBBLE_HEIGHT = 52
BUBBLE_RADIUS = 26
BOTTOM_MARGIN = 80

# Colors -- sourced from theme module (always dark overlay)
BG_COLOR = BUBBLE_BG
ACCENT_RECORDING = BUBBLE_ACCENT_RECORDING
ACCENT_TRANSCRIBING = BUBBLE_ACCENT_TRANSCRIBING
ACCENT_PROCESSING = BUBBLE_ACCENT_PROCESSING
ACCENT_DONE = BUBBLE_ACCENT_DONE
TEXT_COLOR = BUBBLE_TEXT

# Sound bar config
NUM_BARS = 5
BAR_WIDTH = 4
BAR_GAP = 3
BAR_MIN_HEIGHT = 4
BAR_MAX_HEIGHT = 22

# Spinner config
SPINNER_SIZE = 18
SPINNER_ARC = 270

# Animation timing
FADE_DURATION = 200
DONE_DISPLAY_MS = 800


class StatusBubble(QWidget):
    """Animated pill-shaped status overlay."""

    statusSignal = pyqtSignal(str)
    audioLevelSignal = pyqtSignal(float)
    closeSignal = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_window()
        self._init_state()
        self._init_animations()
        self._connect_signals()

    # -------------------------------------------------------------------
    # Setup
    # -------------------------------------------------------------------

    def _setup_window(self):
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WA_ShowWithoutActivating, True)
        self.setFixedSize(BUBBLE_WIDTH, BUBBLE_HEIGHT)

    def _init_state(self):
        self._state = 'idle'  # idle, recording, transcribing, processing, done
        self._opacity = 0.0
        self._audio_level = 0.0
        self._bar_heights = [BAR_MIN_HEIGHT] * NUM_BARS
        self._bar_targets = [BAR_MIN_HEIGHT] * NUM_BARS
        self._spinner_angle = 0
        self._tick_count = 0

    def _init_animations(self):
        # Master tick timer -- drives all animations at 60fps
        self._tick_timer = QTimer(self)
        self._tick_timer.setInterval(16)  # ~60fps
        self._tick_timer.timeout.connect(self._on_tick)

        # Fade animation
        self._fade_anim = QPropertyAnimation(self, b'opacity')
        self._fade_anim.setDuration(FADE_DURATION)
        self._fade_anim.setEasingCurve(QEasingCurve.InOutCubic)

        # Auto-hide timer for "done" state
        self._done_timer = QTimer(self)
        self._done_timer.setSingleShot(True)
        self._done_timer.timeout.connect(self._fade_out)

    def _connect_signals(self):
        self.statusSignal.connect(self.updateStatus)
        self.audioLevelSignal.connect(self._on_audio_level)

    # -------------------------------------------------------------------
    # Qt Properties for animation
    # -------------------------------------------------------------------

    def _get_opacity(self):
        return self._opacity

    def _set_opacity(self, val):
        self._opacity = val
        self.setWindowOpacity(val)
        self.update()

    opacity = pyqtProperty(float, _get_opacity, _set_opacity)

    # -------------------------------------------------------------------
    # Positioning
    # -------------------------------------------------------------------

    def _position_on_screen(self):
        screen = QGuiApplication.primaryScreen()
        if not screen:
            return
        geo = screen.availableGeometry()
        x = geo.x() + (geo.width() - self.width()) // 2
        y = geo.y() + geo.height() - self.height() - BOTTOM_MARGIN
        self.move(x, y)

    # -------------------------------------------------------------------
    # State management
    # -------------------------------------------------------------------

    @pyqtSlot(str)
    def updateStatus(self, status):
        """Handle status transitions."""
        if status == 'recording':
            self._transition_to('recording')
        elif status == 'transcribing':
            self._transition_to('transcribing')
        elif status == 'processing':
            self._transition_to('processing')
        elif status == 'done':
            self._transition_to('done')
        elif status in ('idle', 'error', 'cancel'):
            if self._state == 'idle':
                return
            self._transition_to('idle')

    def _transition_to(self, new_state):
        old_state = self._state
        self._state = new_state

        if new_state == 'idle':
            self._fade_out()
            return

        if new_state == 'done':
            self._done_timer.start(DONE_DISPLAY_MS)
            self.update()
            return

        # Start showing if we were idle
        if old_state == 'idle':
            self._position_on_screen()
            self.show()
            self._fade_in()
            self._tick_timer.start()
        else:
            self.update()

    def _fade_in(self):
        self._fade_anim.stop()
        self._fade_anim.setStartValue(self._opacity)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.start()

    def _fade_out(self):
        self._fade_anim.stop()
        self._fade_anim.setStartValue(self._opacity)
        self._fade_anim.setEndValue(0.0)
        self._fade_anim.finished.connect(self._on_fade_out_done)
        self._fade_anim.start()

    def _on_fade_out_done(self):
        self._fade_anim.finished.disconnect(self._on_fade_out_done)
        self._tick_timer.stop()
        self._state = 'idle'
        self._audio_level = 0.0
        self._bar_heights = [BAR_MIN_HEIGHT] * NUM_BARS
        self.hide()

    # -------------------------------------------------------------------
    # Audio level
    # -------------------------------------------------------------------

    @pyqtSlot(float)
    def _on_audio_level(self, level):
        """Receive audio RMS level (0.0 - 1.0)."""
        self._audio_level = max(0.0, min(1.0, level))
        # Set new random-ish bar targets based on audio level
        import random
        for i in range(NUM_BARS):
            base = BAR_MIN_HEIGHT + (BAR_MAX_HEIGHT - BAR_MIN_HEIGHT) * self._audio_level
            jitter = random.uniform(0.5, 1.2)
            self._bar_targets[i] = max(BAR_MIN_HEIGHT, min(BAR_MAX_HEIGHT, base * jitter))

    # -------------------------------------------------------------------
    # Animation tick
    # -------------------------------------------------------------------

    def _on_tick(self):
        self._tick_count += 1

        if self._state == 'recording':
            # Smoothly interpolate bar heights toward targets
            for i in range(NUM_BARS):
                diff = self._bar_targets[i] - self._bar_heights[i]
                self._bar_heights[i] += diff * 0.3

            # Slowly decay targets when no audio
            if self._audio_level < 0.01:
                for i in range(NUM_BARS):
                    self._bar_targets[i] = max(BAR_MIN_HEIGHT,
                                               self._bar_targets[i] * 0.92)

        elif self._state in ('transcribing', 'processing'):
            # Spinner rotation
            self._spinner_angle = (self._spinner_angle + 6) % 360

        self.update()

    # -------------------------------------------------------------------
    # Painting
    # -------------------------------------------------------------------

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing, True)
        painter.setRenderHint(QPainter.TextAntialiasing, True)

        # Draw pill background
        self._draw_background(painter)

        # Draw state-specific content
        if self._state == 'recording':
            self._draw_recording(painter)
        elif self._state == 'transcribing':
            self._draw_spinner_state(painter, 'Transcribing...', ACCENT_TRANSCRIBING)
        elif self._state == 'processing':
            self._draw_spinner_state(painter, 'Processing...', ACCENT_PROCESSING)
        elif self._state == 'done':
            self._draw_done(painter)

        painter.end()

    def _draw_background(self, painter):
        path = QPainterPath()
        path.addRoundedRect(QRectF(0, 0, self.width(), self.height()),
                            BUBBLE_RADIUS, BUBBLE_RADIUS)
        painter.setPen(Qt.NoPen)
        painter.setBrush(QBrush(BG_COLOR))
        painter.drawPath(path)

    def _draw_recording(self, painter):
        """Draw pulsing dot + animated sound bars + 'Recording' text."""
        x_cursor = 18

        # Pulsing red dot
        pulse = 0.7 + 0.3 * math.sin(self._tick_count * 0.08)
        dot_color = QColor(ACCENT_RECORDING)
        dot_color.setAlphaF(pulse)
        painter.setBrush(QBrush(dot_color))
        painter.setPen(Qt.NoPen)
        dot_radius = 5
        dot_y = self.height() / 2
        painter.drawEllipse(int(x_cursor - dot_radius), int(dot_y - dot_radius),
                            dot_radius * 2, dot_radius * 2)
        x_cursor += dot_radius * 2 + 10

        # Sound bars
        bars_total_width = NUM_BARS * BAR_WIDTH + (NUM_BARS - 1) * BAR_GAP
        bar_x = x_cursor
        bar_center_y = self.height() / 2

        for i in range(NUM_BARS):
            h = self._bar_heights[i]
            bx = bar_x + i * (BAR_WIDTH + BAR_GAP)
            by = bar_center_y - h / 2

            # Gradient bar
            grad = QLinearGradient(bx, by, bx, by + h)
            grad.setColorAt(0, ACCENT_RECORDING)
            color_end = QColor(ACCENT_RECORDING)
            color_end.setAlphaF(0.5)
            grad.setColorAt(1, color_end)

            painter.setBrush(QBrush(grad))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(QRectF(bx, by, BAR_WIDTH, h), 2, 2)

        x_cursor = bar_x + bars_total_width + 12

        # Text
        font = QFont(FONT_FAMILY.split(',')[0].strip(), 11)
        font.setWeight(QFont.Medium)
        painter.setFont(font)
        painter.setPen(QPen(TEXT_COLOR))
        text_rect = QRectF(x_cursor, 0, self.width() - x_cursor - 10, self.height())
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, 'Recording')

    def _draw_spinner_state(self, painter, text, accent_color):
        """Draw spinner + text for transcribing/processing states."""
        x_cursor = 18

        # Spinner
        spinner_rect = QRectF(
            x_cursor,
            (self.height() - SPINNER_SIZE) / 2,
            SPINNER_SIZE,
            SPINNER_SIZE,
        )

        pen = QPen(QColor(255, 255, 255, 40), 2.5)
        pen.setCapStyle(Qt.RoundCap)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(spinner_rect)

        pen_active = QPen(accent_color, 2.5)
        pen_active.setCapStyle(Qt.RoundCap)
        painter.setPen(pen_active)
        start_angle = -self._spinner_angle * 16
        span_angle = SPINNER_ARC * 16
        painter.drawArc(spinner_rect.toRect(), start_angle, span_angle)

        x_cursor += SPINNER_SIZE + 12

        # Text
        font = QFont(FONT_FAMILY.split(',')[0].strip(), 11)
        font.setWeight(QFont.Medium)
        painter.setFont(font)
        painter.setPen(QPen(TEXT_COLOR))
        text_rect = QRectF(x_cursor, 0, self.width() - x_cursor - 10, self.height())
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, text)

    def _draw_done(self, painter):
        """Draw checkmark + 'Done' text."""
        x_cursor = 18

        # Checkmark circle
        circle_size = 20
        cx = x_cursor
        cy = (self.height() - circle_size) / 2
        painter.setBrush(QBrush(ACCENT_DONE))
        painter.setPen(Qt.NoPen)
        painter.drawEllipse(QRectF(cx, cy, circle_size, circle_size))

        # Checkmark path
        pen = QPen(QColor(255, 255, 255), 2.0)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        # Draw a check mark
        check_x = cx + 5
        check_y = cy + circle_size / 2
        painter.drawLine(int(check_x), int(check_y),
                         int(check_x + 3), int(check_y + 4))
        painter.drawLine(int(check_x + 3), int(check_y + 4),
                         int(check_x + 10), int(check_y - 4))

        x_cursor += circle_size + 12

        # Text
        font = QFont(FONT_FAMILY.split(',')[0].strip(), 11)
        font.setWeight(QFont.Medium)
        painter.setFont(font)
        painter.setPen(QPen(TEXT_COLOR))
        text_rect = QRectF(x_cursor, 0, self.width() - x_cursor - 10, self.height())
        painter.drawText(text_rect, Qt.AlignVCenter | Qt.AlignLeft, 'Done')

    # -------------------------------------------------------------------
    # Event overrides
    # -------------------------------------------------------------------

    def closeEvent(self, event):
        self.closeSignal.emit()
        super().closeEvent(event)


# Keep backward-compatible name
StatusWindow = StatusBubble


if __name__ == '__main__':
    app = QApplication(sys.argv)
    bubble = StatusBubble()

    # Demo sequence
    QTimer.singleShot(500, lambda: bubble.statusSignal.emit('recording'))
    QTimer.singleShot(1000, lambda: bubble.audioLevelSignal.emit(0.3))
    QTimer.singleShot(1500, lambda: bubble.audioLevelSignal.emit(0.7))
    QTimer.singleShot(2000, lambda: bubble.audioLevelSignal.emit(0.9))
    QTimer.singleShot(2500, lambda: bubble.audioLevelSignal.emit(0.2))
    QTimer.singleShot(3500, lambda: bubble.statusSignal.emit('transcribing'))
    QTimer.singleShot(5500, lambda: bubble.statusSignal.emit('processing'))
    QTimer.singleShot(7500, lambda: bubble.statusSignal.emit('done'))
    QTimer.singleShot(9000, lambda: bubble.statusSignal.emit('idle'))

    sys.exit(app.exec_())
