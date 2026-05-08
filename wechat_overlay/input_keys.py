from __future__ import annotations

from enum import Enum


class KeyAction(Enum):
    SEND = "send"
    NEWLINE = "newline"


def classify_enter_key(*, shift: bool, control: bool) -> KeyAction:
    if shift or control:
        return KeyAction.NEWLINE
    return KeyAction.SEND
