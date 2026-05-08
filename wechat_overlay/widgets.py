from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QTextEdit

from wechat_overlay.input_keys import KeyAction, classify_enter_key


class PlaintextEditor(QTextEdit):
    def __init__(self, on_send: Callable[[], None]) -> None:
        super().__init__()
        self._on_send = on_send

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            modifiers = event.modifiers()
            action = classify_enter_key(
                shift=bool(modifiers & Qt.KeyboardModifier.ShiftModifier),
                control=bool(modifiers & Qt.KeyboardModifier.ControlModifier),
            )
            if action is KeyAction.SEND:
                self._on_send()
                event.accept()
                return

        super().keyPressEvent(event)
