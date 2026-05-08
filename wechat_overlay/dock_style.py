from __future__ import annotations


def collapsed_label(name: str) -> str:
    return "‹"


def expanded_label() -> str:
    return ">"


def panel_stylesheet() -> str:
    return (
        "QWidget { background: rgba(255, 248, 220, 245); color: #111827; border: 2px solid rgba(217, 119, 6, 230); border-radius: 14px; }"
        "QLineEdit, QTextEdit { background: rgba(255,255,255,250); color: #111827; border: 1px solid rgba(146, 64, 14, 160); border-radius: 10px; padding: 8px; }"
        "QPushButton { background: rgba(245, 158, 11, 245); color: #111827; border: 1px solid rgba(146, 64, 14, 180); border-radius: 10px; padding: 8px 12px; font-weight: 700; }"
        "QPushButton:hover { background: rgba(251, 191, 36, 255); }"
        "QCheckBox { background: transparent; color: #111827; }"
        "QLabel { background: transparent; color: #111827; }"
    )


def collapsed_button_stylesheet() -> str:
    return (
        "QPushButton { background: rgba(245, 158, 11, 250); color: #111827; border: 1px solid rgba(146, 64, 14, 230);"
        "border-radius: 12px;"
        "font-size: 15px; font-weight: 900; padding: 0; }"
        "QPushButton:hover { background: rgba(251, 191, 36, 255); }"
    )


def overlay_message_stylesheet() -> str:
    return (
        "background-color: rgba(255, 214, 102, 245);"
        "color: #111827;"
        "border: 2px solid rgba(146, 64, 14, 220);"
        "border-radius: 8px;"
        "padding: 6px 10px;"
        "font-size: 14px;"
        "font-weight: 700;"
    )
