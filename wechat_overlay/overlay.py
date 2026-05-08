from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Callable

import pyperclip

from PySide6.QtCore import Qt, QRect, QTimer
from PySide6.QtWidgets import QApplication, QLabel, QPushButton, QWidget

from wechat_overlay.dock_style import overlay_message_stylesheet


@dataclass(frozen=True)
class OverlayMessage:
    plaintext: str
    x: int
    y: int
    width: int
    height: int
    side: str = "left"

    @property
    def identity(self) -> tuple[str, int, int, int, int]:
        return (self.plaintext, self.x, self.y, self.width, self.height)


@dataclass(frozen=True)
class OverlayBubbleRect:
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class BubbleSize:
    width: int
    height: int
    full_height: int
    collapsed: bool


def overlay_bubble_max_width(chat_width: int) -> int:
    return max(80, int(chat_width * 0.90))


def choose_bubble_size(
    *,
    min_width: int,
    max_width: int,
    original_height: int,
    height_for_width: Callable[[int], int],
    step: int = 20,
) -> BubbleSize:
    width = max(1, min_width)
    max_width = max(width, max_width)
    original_height = max(1, original_height)
    while width < max_width:
        height = height_for_width(width)
        if height <= original_height:
            return BubbleSize(width=width, height=height, full_height=height, collapsed=False)
        width = min(max_width, width + step)
    full_height = height_for_width(max_width)
    if full_height <= original_height:
        return BubbleSize(width=max_width, height=full_height, full_height=full_height, collapsed=False)
    return BubbleSize(width=max_width, height=original_height, full_height=full_height, collapsed=True)


def adaptive_bubble_rect(
    message: OverlayMessage,
    overlay_bounds: QRect,
    content_width: int,
    content_height: int,
    *,
    min_width: int = 44,
    min_height: int = 28,
    edge_margin: int = 80,
) -> OverlayBubbleRect:
    """Size plaintext bubbles to their content while keeping the original message anchor."""
    width = max(min_width, content_width)
    height = max(min_height, content_height)
    overlay_left = overlay_bounds.x()
    overlay_top = overlay_bounds.y()
    overlay_right = overlay_left + overlay_bounds.width()
    overlay_bottom = overlay_top + overlay_bounds.height()

    x = overlay_right - edge_margin - width if message.side == "right" else overlay_left + edge_margin
    y = message.y

    x = min(max(x, overlay_left), max(overlay_left, overlay_right - width))
    y = min(max(y, overlay_top), max(overlay_top, overlay_bottom - height))
    return OverlayBubbleRect(x=x, y=y, width=width, height=height)


class OverlayWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self._labels: list[QLabel] = []
        self._copy_buttons: list[QPushButton] = []
        self._expanded_label: QLabel | None = None
        self._expanded_identity: tuple[str, int, int, int, int] | None = None
        self._copy_popup: QLabel | None = None
        self._last_copied_text = ""
        self._last_render_state: tuple[tuple[tuple[str, int, int, int, int, str], ...], int, int, int, int, tuple[str, int, int, int, int] | None] | None = None

    def follow(self, x: int, y: int, width: int, height: int) -> None:
        self.setGeometry(QRect(x, y, width, height))

    def render_messages(self, messages: list[OverlayMessage]) -> None:
        render_state = (
            tuple((message.plaintext, message.x, message.y, message.width, message.height, message.side) for message in messages),
            self.x(),
            self.y(),
            self.width(),
            self.height(),
            self._expanded_identity,
        )
        if render_state == self._last_render_state:
            return
        self._last_render_state = render_state
        expanded_identity = self._expanded_identity
        old_labels = {label.property("message_identity"): label for label in self._labels}
        old_buttons = {button.property("message_identity"): button for button in self._copy_buttons}
        reused_labels: set[QLabel] = set()
        reused_buttons: set[QPushButton] = set()
        self._labels.clear()
        self._copy_buttons.clear()
        self._expanded_label = None

        for message in messages:
            label = old_labels.get(message.identity)
            if label is None:
                label = ClickableBubbleLabel(message.plaintext, self, self._toggle_label)
            else:
                reused_labels.add(label)
                label.setText(message.plaintext)
            label.setWordWrap(True)
            label.setStyleSheet(overlay_message_stylesheet())
            max_width = overlay_bubble_max_width(self.width())
            label.setMaximumWidth(max_width)
            label.adjustSize()
            min_width = min(max_width, max(44, min(label.sizeHint().width(), max_width)))
            size = choose_bubble_size(
                min_width=min_width,
                max_width=max_width,
                original_height=max(28, message.height),
                height_for_width=lambda width, current_label=label: current_label.heightForWidth(width) if current_label.hasHeightForWidth() else current_label.sizeHint().height(),
            )
            collapsed_rect = adaptive_bubble_rect(message, self.geometry(), size.width, size.height)
            expanded_rect = adaptive_bubble_rect(message, self.geometry(), size.width, size.full_height)
            should_restore_expanded = size.collapsed and message.identity == expanded_identity
            label.setProperty("collapsed_rect", collapsed_rect)
            label.setProperty("expanded_rect", expanded_rect)
            label.setProperty("message_identity", message.identity)
            label.setProperty("expanded", should_restore_expanded)
            label.setProperty("collapsible", size.collapsed)
            label.setToolTip("点击展开/收起" if size.collapsed else "")
            active_rect = expanded_rect if should_restore_expanded else collapsed_rect
            label.setGeometry(active_rect.x - self.x(), active_rect.y - self.y(), active_rect.width, active_rect.height)
            label.show()
            copy_button = old_buttons.get(message.identity)
            if copy_button is None:
                copy_button = QPushButton("⧉", self)
            else:
                reused_buttons.add(copy_button)
            copy_button.setFixedSize(22, 22)
            copy_button.setProperty("message_identity", message.identity)
            copy_button.setToolTip("复制明文")
            copy_button.setStyleSheet(
                "QPushButton { background: rgba(255,255,255,235); border: 1px solid rgba(217,119,6,200); border-radius: 11px; padding: 0; color: #92400e; font-weight: 700; }"
                "QPushButton:pressed { background: rgba(245,158,11,245); color: white; padding-top: 2px; padding-left: 1px; }"
            )
            if copy_button not in reused_buttons:
                copy_button.clicked.connect(lambda _checked=False, text=message.plaintext: self._copy_text(text))
                copy_button.pressed.connect(lambda button=copy_button: self._press_copy_button(button))
                copy_button.released.connect(lambda button=copy_button: self._release_copy_button(button))
            else:
                copy_button.setProperty("copy_text", message.plaintext)
            self._place_copy_button(copy_button, message, collapsed_rect)
            copy_button.show()
            self._labels.append(label)
            self._copy_buttons.append(copy_button)
            if should_restore_expanded:
                self._expanded_label = label

        for label in old_labels.values():
            if label not in reused_labels and label not in self._labels:
                label.deleteLater()
        for button in old_buttons.values():
            if button not in reused_buttons and button not in self._copy_buttons:
                button.deleteLater()

    def _toggle_label(self, label: QLabel) -> None:
        self._last_render_state = None
        if not label.property("collapsible"):
            return
        if label.property("expanded") is True:
            self._collapse_label(label)
            self._expanded_label = None
            self._expanded_identity = None
            return
        if self._expanded_label is not None and self._expanded_label is not label:
            self._collapse_label(self._expanded_label)
        self._expand_label(label)
        self._expanded_label = label
        self._expanded_identity = label.property("message_identity")

    def _collapse_label(self, label: QLabel) -> None:
        rect = label.property("collapsed_rect")
        if isinstance(rect, OverlayBubbleRect):
            label.setGeometry(rect.x - self.x(), rect.y - self.y(), rect.width, rect.height)
        label.setProperty("expanded", False)

    def _expand_label(self, label: QLabel) -> None:
        rect = label.property("expanded_rect")
        if isinstance(rect, OverlayBubbleRect):
            label.setGeometry(rect.x - self.x(), rect.y - self.y(), rect.width, rect.height)
        label.setProperty("expanded", True)

    def _place_copy_button(self, button: QPushButton, message: OverlayMessage, rect: OverlayBubbleRect, *, gap: int = 6) -> None:
        if message.side == "right":
            x = rect.x - self.x() - button.width() - gap
        else:
            x = rect.x - self.x() + rect.width + gap
        y = rect.y - self.y() + max(0, (rect.height - button.height()) // 2)
        x = max(0, min(x, max(0, self.width() - button.width())))
        y = max(0, min(y, max(0, self.height() - button.height())))
        button.setGeometry(x, y, button.width(), button.height())
        button.setProperty("rest_geometry", button.geometry())

    def _press_copy_button(self, button: QPushButton) -> None:
        rest = button.property("rest_geometry")
        if not isinstance(rest, QRect):
            rest = button.geometry()
            button.setProperty("rest_geometry", rest)
        button.setGeometry(rest.x() + 2, rest.y() + 2, rest.width(), rest.height())

    def _release_copy_button(self, button: QPushButton) -> None:
        rest = button.property("rest_geometry")
        if isinstance(rest, QRect):
            button.setGeometry(rest)

    def _copy_text(self, text: str) -> None:
        self._last_copied_text = text
        pyperclip.copy(text)
        app = QApplication.instance()
        if app is not None:
            app.clipboard().setText(text)
            app.processEvents()
        self._show_copy_popup()

    def _show_copy_popup(self) -> None:
        if self._copy_popup is not None:
            self._copy_popup.deleteLater()
        popup = QLabel("复制成功")
        popup.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        popup.setStyleSheet("QLabel { background: rgba(22, 163, 74, 235); color: white; border-radius: 10px; padding: 6px 12px; font-weight: 700; }")
        popup.adjustSize()
        screen = QApplication.primaryScreen().geometry() if QApplication.primaryScreen() is not None else QRect(self.x(), self.y(), self.width(), self.height())
        rect = self.copy_popup_rect(screen, popup.width(), popup.height())
        popup.setGeometry(rect)
        popup.show()
        popup.raise_()
        self._copy_popup = popup
        QTimer.singleShot(1200, popup.hide)

    def copy_popup_rect(self, screen_geometry: QRect, popup_width: int, popup_height: int) -> QRect:
        return QRect(
            screen_geometry.x() + max(0, (screen_geometry.width() - popup_width) // 2),
            screen_geometry.y() + max(0, (screen_geometry.height() - popup_height) // 2),
            popup_width,
            popup_height,
        )


class ClickableBubbleLabel(QLabel):
    def __init__(self, text: str, parent: QWidget, on_click: Callable[[QLabel], None]) -> None:
        super().__init__(text, parent)
        self._on_click = on_click

    def mousePressEvent(self, event) -> None:
        self._on_click(self)
        if event is not None:
            super().mousePressEvent(event)
