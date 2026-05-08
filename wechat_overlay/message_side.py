from __future__ import annotations

from collections import deque


class SentCipherRegistry:
    def __init__(self, max_items: int = 100) -> None:
        self._items: deque[str] = deque(maxlen=max_items)

    def remember(self, ciphertext: str) -> None:
        self._items.append(ciphertext)

    def contains(self, ciphertext: str) -> bool:
        return ciphertext in self._items


def message_side(ciphertext: str, *, is_file_transfer_chat: bool, sent_registry: SentCipherRegistry) -> str:
    if sent_registry.contains(ciphertext) or is_file_transfer_chat:
        return "right"
    return "left"
