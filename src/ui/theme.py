"""Shared theming infrastructure for WhisperWriter UI.

Detects the system dark/light preference and provides:
- Color palettes for both themes
- QSS stylesheets that adapt to the active theme
- A consistent font stack that works on Linux, macOS, and Windows
"""

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QPalette
from PyQt5.QtWidgets import QApplication


# ---------------------------------------------------------------------------
# System font stack (prefer platform-native, fallback gracefully)
# ---------------------------------------------------------------------------

FONT_FAMILY = "Inter, Cantarell, Noto Sans, Segoe UI, Helvetica Neue, sans-serif"
FONT_FAMILY_MONO = "JetBrains Mono, Fira Code, Consolas, monospace"


# ---------------------------------------------------------------------------
# Dark mode detection
# ---------------------------------------------------------------------------

def is_dark_theme() -> bool:
    """Detect whether the system (or Qt platform) is using a dark theme.

    Checks multiple signals in priority order:
    1. Qt palette lightness (most reliable on KDE/GNOME with qt5ct, Breeze, etc.)
    2. Environment hints (GTK_THEME, etc.)
    """
    app = QApplication.instance()
    if app is not None:
        palette = app.palette()
        # If the window background is darker than mid-gray, it's a dark theme
        bg = palette.color(QPalette.Window)
        return bg.lightnessF() < 0.5
    return False


# ---------------------------------------------------------------------------
# Color palettes
# ---------------------------------------------------------------------------

class _LightPalette:
    """Colors for light system theme."""
    # Window / surface
    window_bg = QColor(255, 255, 255, 220)
    surface = QColor(250, 250, 250)
    surface_hover = QColor(240, 240, 240)
    surface_pressed = QColor(224, 224, 224)

    # Text
    text_primary = QColor(32, 32, 32)
    text_secondary = QColor(64, 64, 64)
    text_muted = QColor(128, 128, 128)

    # Borders
    border = QColor(192, 192, 192)
    border_focus = QColor(74, 144, 217)
    border_subtle = QColor(212, 212, 212)

    # Accent
    accent = QColor(74, 144, 217)
    accent_hover = QColor(58, 123, 200)
    accent_text = QColor(255, 255, 255)

    # Tab bar
    tab_bg = QColor(232, 232, 232)
    tab_selected_bg = QColor(255, 255, 255)
    tab_border = QColor(192, 192, 192)

    # Input fields
    input_bg = QColor(250, 250, 250)

    # Group box
    groupbox_border = QColor(212, 212, 212)

    # Close button
    close_text = QColor(64, 64, 64)
    close_hover = QColor(0, 0, 0)


class _DarkPalette:
    """Colors for dark system theme."""
    # Window / surface
    window_bg = QColor(32, 32, 36, 230)
    surface = QColor(44, 44, 50)
    surface_hover = QColor(54, 54, 62)
    surface_pressed = QColor(64, 64, 72)

    # Text
    text_primary = QColor(230, 230, 235)
    text_secondary = QColor(190, 190, 200)
    text_muted = QColor(140, 140, 155)

    # Borders
    border = QColor(70, 70, 80)
    border_focus = QColor(100, 160, 240)
    border_subtle = QColor(58, 58, 66)

    # Accent
    accent = QColor(100, 160, 240)
    accent_hover = QColor(80, 140, 220)
    accent_text = QColor(255, 255, 255)

    # Tab bar
    tab_bg = QColor(44, 44, 50)
    tab_selected_bg = QColor(54, 54, 62)
    tab_border = QColor(70, 70, 80)

    # Input fields
    input_bg = QColor(38, 38, 44)

    # Group box
    groupbox_border = QColor(60, 60, 68)

    # Close button
    close_text = QColor(190, 190, 200)
    close_hover = QColor(255, 255, 255)


def get_palette():
    """Return the appropriate palette for the current system theme."""
    return _DarkPalette if is_dark_theme() else _LightPalette


# ---------------------------------------------------------------------------
# Helper: QColor -> CSS rgba string
# ---------------------------------------------------------------------------

def _c(color: QColor) -> str:
    """Convert a QColor to a CSS rgba() string."""
    return f"rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha()})"


def _hex(color: QColor) -> str:
    """Convert a QColor to a hex string (no alpha)."""
    return f"#{color.red():02x}{color.green():02x}{color.blue():02x}"


# ---------------------------------------------------------------------------
# QSS generators
# ---------------------------------------------------------------------------

def base_window_qss() -> str:
    """Return QSS for the close button in BaseWindow."""
    p = get_palette()
    return f"""
        QPushButton#close_button {{
            background-color: transparent;
            border: none;
            color: {_hex(p.close_text)};
            font-size: 16px;
        }}
        QPushButton#close_button:hover {{
            color: {_hex(p.close_hover)};
        }}
    """


def title_label_qss() -> str:
    """Return QSS for the title label in BaseWindow."""
    p = get_palette()
    return f"color: {_hex(p.text_secondary)};"


def main_window_button_qss() -> str:
    """Return QSS for buttons in MainWindow."""
    p = get_palette()
    return f"""
        QPushButton {{
            background-color: {_c(p.surface)};
            border: 1px solid {_hex(p.border)};
            border-radius: 6px;
            color: {_hex(p.text_primary)};
            font-family: {FONT_FAMILY};
            font-size: 12px;
            padding: 8px 16px;
        }}
        QPushButton:hover {{
            background-color: {_c(p.surface_hover)};
        }}
        QPushButton:pressed {{
            background-color: {_c(p.surface_pressed)};
        }}
    """


def settings_window_qss() -> str:
    """Return the full QSS stylesheet for SettingsWindow."""
    p = get_palette()
    return f"""
        QTabWidget::pane {{
            border: 1px solid {_hex(p.border_subtle)};
            border-radius: 6px;
            background: transparent;
        }}
        QTabBar::tab {{
            background: {_c(p.tab_bg)};
            border: 1px solid {_hex(p.tab_border)};
            border-bottom: none;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            padding: 6px 14px;
            margin-right: 2px;
            font-size: 11px;
            color: {_hex(p.text_secondary)};
        }}
        QTabBar::tab:selected {{
            background: {_c(p.tab_selected_bg)};
            border-bottom: 2px solid {_hex(p.accent)};
            font-weight: bold;
            color: {_hex(p.text_primary)};
        }}
        QTabBar::tab:hover:!selected {{
            background: {_c(p.surface_hover)};
        }}
        QGroupBox {{
            font-weight: bold;
            font-size: 11px;
            border: 1px solid {_hex(p.groupbox_border)};
            border-radius: 6px;
            margin-top: 12px;
            padding-top: 16px;
            color: {_hex(p.text_primary)};
        }}
        QGroupBox::title {{
            subcontrol-origin: margin;
            left: 12px;
            padding: 0 4px;
            color: {_hex(p.text_primary)};
        }}
        QLabel {{
            color: {_hex(p.text_primary)};
        }}
        QLineEdit, QComboBox {{
            padding: 4px 8px;
            border: 1px solid {_hex(p.border)};
            border-radius: 4px;
            background: {_c(p.input_bg)};
            color: {_hex(p.text_primary)};
            min-height: 24px;
        }}
        QLineEdit:focus, QComboBox:focus {{
            border: 1px solid {_hex(p.border_focus)};
        }}
        QComboBox::drop-down {{
            border: none;
        }}
        QComboBox QAbstractItemView {{
            background: {_c(p.surface)};
            color: {_hex(p.text_primary)};
            border: 1px solid {_hex(p.border)};
            selection-background-color: {_hex(p.accent)};
            selection-color: {_hex(p.accent_text)};
        }}
        QPushButton {{
            padding: 6px 16px;
            border: 1px solid {_hex(p.border)};
            border-radius: 4px;
            background: {_c(p.surface)};
            color: {_hex(p.text_primary)};
            min-height: 28px;
        }}
        QPushButton:hover {{
            background: {_c(p.surface_hover)};
        }}
        QPushButton#save_button {{
            background: {_hex(p.accent)};
            color: {_hex(p.accent_text)};
            border: none;
            font-weight: bold;
        }}
        QPushButton#save_button:hover {{
            background: {_hex(p.accent_hover)};
        }}
        QCheckBox {{
            spacing: 6px;
            color: {_hex(p.text_primary)};
        }}
        QCheckBox::indicator {{
            width: 16px;
            height: 16px;
        }}
        QTextEdit {{
            padding: 4px;
            border: 1px solid {_hex(p.border)};
            border-radius: 4px;
            background: {_c(p.input_bg)};
            color: {_hex(p.text_primary)};
        }}
        QScrollArea {{
            background: transparent;
            border: none;
        }}
        QScrollArea > QWidget > QWidget {{
            background: transparent;
        }}
        QToolButton {{
            color: {_hex(p.text_muted)};
        }}
        QToolButton:hover {{
            color: {_hex(p.text_primary)};
        }}
    """


# ---------------------------------------------------------------------------
# Status bubble colors (always dark overlay -- intentional)
# These remain independent from the system theme.
# ---------------------------------------------------------------------------

BUBBLE_BG = QColor(24, 24, 28, 230)
BUBBLE_TEXT = QColor(255, 255, 255, 230)
BUBBLE_ACCENT_RECORDING = QColor(239, 68, 68)
BUBBLE_ACCENT_TRANSCRIBING = QColor(234, 179, 8)
BUBBLE_ACCENT_PROCESSING = QColor(99, 102, 241)
BUBBLE_ACCENT_DONE = QColor(34, 197, 94)
