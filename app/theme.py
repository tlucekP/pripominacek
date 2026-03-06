from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtWidgets import QApplication


@dataclass(slots=True, frozen=True)
class Theme:
    bg: str
    surface: str
    text: str
    muted: str
    accent: str
    border: str


THEMES: dict[str, Theme] = {
    "light": Theme(
        bg="#F6F7FB",
        surface="#FFFFFF",
        text="#111827",
        muted="#6B7280",
        accent="#3B82F6",
        border="#E5E7EB",
    ),
    "dark": Theme(
        bg="#111827",
        surface="#1F2937",
        text="#F9FAFB",
        muted="#9CA3AF",
        accent="#60A5FA",
        border="#374151",
    ),
    "pastel_green": Theme(
        bg="#F3FBF6",
        surface="#FFFFFF",
        text="#0F172A",
        muted="#64748B",
        accent="#34D399",
        border="#D1FAE5",
    ),
    "pastel_red": Theme(
        bg="#FFF5F5",
        surface="#FFFFFF",
        text="#0F172A",
        muted="#64748B",
        accent="#FB7185",
        border="#FFE4E6",
    ),
    "pastel_yellow": Theme(
        bg="#FFFBEB",
        surface="#FFFFFF",
        text="#0F172A",
        muted="#64748B",
        accent="#FBBF24",
        border="#FEF3C7",
    ),
}


def _hex_to_rgb(color: str) -> tuple[int, int, int]:
    cleaned = color.strip().lstrip("#")
    return (int(cleaned[0:2], 16), int(cleaned[2:4], 16), int(cleaned[4:6], 16))


def _rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02X}{:02X}{:02X}".format(*rgb)


def _adjust_color(color: str, factor: float) -> str:
    r, g, b = _hex_to_rgb(color)

    def adjust_channel(channel: int) -> int:
        if factor >= 0:
            return int(channel + (255 - channel) * factor)
        return int(channel * (1 + factor))

    adjusted = (
        max(0, min(255, adjust_channel(r))),
        max(0, min(255, adjust_channel(g))),
        max(0, min(255, adjust_channel(b))),
    )
    return _rgb_to_hex(adjusted)


def _to_rgba(color: str, alpha: int) -> str:
    r, g, b = _hex_to_rgb(color)
    return f"rgba({r}, {g}, {b}, {alpha})"


def is_light(color: str) -> bool:
    r, g, b = _hex_to_rgb(color)
    luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255
    return luminance >= 0.62


def apply_theme(app: QApplication, theme_key: str) -> str:
    key = theme_key if theme_key in THEMES else "light"
    theme = THEMES[key]

    button_text = "#111827" if is_light(theme.accent) else "#FFFFFF"
    hover = _adjust_color(theme.accent, -0.12 if is_light(theme.accent) else 0.12)
    pressed = _adjust_color(theme.accent, -0.22 if is_light(theme.accent) else -0.08)
    surface_alt = _adjust_color(theme.surface, -0.04 if is_light(theme.surface) else 0.08)

    qss = f"""
    QWidget {{
        background-color: {theme.bg};
        color: {theme.text};
        font-family: 'Segoe UI';
        font-size: 13px;
    }}

    QMainWindow, QDialog {{
        background-color: {theme.bg};
    }}

    QLabel {{
        color: {theme.text};
        background: transparent;
    }}

    QLabel[muted='true'] {{
        color: {theme.muted};
    }}

    QGroupBox {{
        background-color: {theme.surface};
        border: 1px solid {theme.border};
        border-radius: 10px;
        margin-top: 12px;
        padding-top: 14px;
    }}

    QGroupBox::title {{
        color: {theme.muted};
        left: 12px;
        padding: 0 4px;
        subcontrol-origin: margin;
    }}

    QTableWidget,
    QTextEdit,
    QLineEdit,
    QTimeEdit,
    QDateEdit,
    QComboBox,
    QListWidget {{
        background-color: {theme.surface};
        border: 1px solid {theme.border};
        border-radius: 8px;
        padding: 5px;
        color: {theme.text};
        selection-background-color: {_to_rgba(theme.accent, 86)};
        selection-color: {theme.text};
    }}

    QComboBox QAbstractItemView {{
        background-color: {theme.surface};
        border: 1px solid {theme.border};
        color: {theme.text};
        selection-background-color: {_to_rgba(theme.accent, 86)};
        selection-color: {theme.text};
    }}

    QTableWidget::item {{
        border-bottom: 1px solid {theme.border};
        padding: 4px;
    }}

    QHeaderView::section {{
        background-color: {surface_alt};
        color: {theme.muted};
        border: 1px solid {theme.border};
        padding: 6px;
        font-weight: 600;
    }}

    QPushButton {{
        background-color: {theme.accent};
        color: {button_text};
        border: 1px solid transparent;
        border-radius: 8px;
        padding: 7px 12px;
        font-weight: 600;
    }}

    QPushButton:hover {{
        background-color: {hover};
    }}

    QPushButton:pressed {{
        background-color: {pressed};
    }}

    QPushButton#secondaryButton {{
        background-color: {theme.surface};
        color: {theme.text};
        border: 1px solid {theme.border};
    }}

    QPushButton#secondaryButton:hover {{
        border-color: {theme.accent};
        background-color: {surface_alt};
    }}

    QCheckBox {{
        spacing: 8px;
    }}

    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border-radius: 4px;
        border: 1px solid {theme.border};
        background: {theme.surface};
    }}

    QCheckBox::indicator:checked {{
        background: {theme.accent};
        border: 1px solid {theme.accent};
    }}

    QTextEdit:focus,
    QLineEdit:focus,
    QTimeEdit:focus,
    QDateEdit:focus,
    QComboBox:focus,
    QTableWidget:focus {{
        border: 1px solid {theme.accent};
    }}
    """

    app.setStyleSheet(qss)
    return key
