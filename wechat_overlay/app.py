from __future__ import annotations

import os
import sys

from PIL import ImageGrab
from PySide6.QtWidgets import QApplication

from wechat_overlay.avatar_side import score_message_side
from wechat_overlay.crypto import decrypt_text, encrypt_text, is_encrypted
from wechat_overlay.dock_layout import DockAreas, Rect, dock_areas_from_message_list
from wechat_overlay.dock_panels import DecryptDockWindow, DockController, ExitDockWindow, InputDockWindow, SettingsDockWindow
from wechat_overlay.key_store import load_key, save_key
from wechat_overlay.message_side import SentCipherRegistry, message_side
from wechat_overlay.overlay import OverlayMessage
from wechat_overlay.single_instance import stop_existing_overlay_processes
from wechat_overlay.wechat_uia import SendSafetyError, WechatWindowCache, foreground_process_id, message_list_rect, send_text_to_current_chat, send_text_to_file_transfer, should_show_overlay


WINDOW_CACHE = WechatWindowCache()
SENT_CIPHERS = SentCipherRegistry()
SIDE_CACHE: dict[tuple[str, int, int, int, int], str] = {}


def wechat_rect(*, allow_overlay_foreground: bool = False) -> DockAreas | None:
    window = WINDOW_CACHE.get()
    if window is None:
        return None
    foreground_pid = foreground_process_id()
    if not should_show_overlay(window.process_id, foreground_pid) and not (allow_overlay_foreground and foreground_pid == os.getpid()):
        return None
    rect = window.wrapper.rectangle()
    wechat = Rect(rect.left, rect.top, rect.width(), rect.height())
    return dock_areas_from_message_list(wechat, message_list_rect(window))


def send_encrypted(key: str, plaintext: str, current_chat_mode: bool) -> None:
    if not key.strip() or not plaintext.strip():
        return
    window = WINDOW_CACHE.get()
    if window is None:
        return
    cipher = encrypt_text(key, plaintext)
    SENT_CIPHERS.remember(cipher)
    try:
        if current_chat_mode:
            send_text_to_current_chat(window, cipher)
        else:
            send_text_to_file_transfer(window, cipher)
    except SendSafetyError:
        return


def decrypt_visible_messages(key_provider, overlay_window=None) -> list[OverlayMessage]:
    key = key_provider()
    if not key.strip():
        return []
    window = WINDOW_CACHE.get()
    if window is None:
        return []

    messages: list[OverlayMessage] = []
    areas = wechat_rect(allow_overlay_foreground=True)
    screenshot = None
    if areas is not None:
        screenshot = ImageGrab.grab((areas.chat.x, areas.chat.y, areas.chat.x + areas.chat.width, areas.chat.y + areas.chat.height))
    for control in window.wrapper.descendants():
        try:
            text = control.window_text().strip()
        except Exception:
            continue
        if not is_encrypted(text):
            continue
        plaintext = decrypt_text(key, text)
        if plaintext is None:
            continue
        rect = control.rectangle()
        row = Rect(rect.left, rect.top, rect.width(), rect.height())
        if screenshot is not None and areas is not None:
            local_chat = Rect(0, 0, areas.chat.width, areas.chat.height)
            local_row = Rect(row.x - areas.chat.x, row.y - areas.chat.y, row.width, row.height)
            identity = (text, row.x, row.y, row.width, row.height)
            detected_side = score_message_side(screenshot, local_chat, local_row).side
            side = detected_side or SIDE_CACHE.get(identity) or message_side(text, is_file_transfer_chat=False, sent_registry=SENT_CIPHERS)
            SIDE_CACHE[identity] = side
        else:
            side = message_side(text, is_file_transfer_chat=False, sent_registry=SENT_CIPHERS)
        messages.append(OverlayMessage(plaintext, row.x, row.y, row.width, row.height, side=side))
    return messages


def main() -> int:
    stop_existing_overlay_processes()
    app = QApplication(sys.argv)
    settings_panel = SettingsDockWindow()
    settings_panel.set_key(load_key())
    settings_panel.set_key_changed_handler(save_key)
    decrypt_panel = DecryptDockWindow(lambda: decrypt_visible_messages(settings_panel.key_provider, decrypt_panel.overlay), settings_panel.key_provider)
    input_panel = InputDockWindow(send_encrypted, settings_panel.key_provider)
    exit_panel = ExitDockWindow()
    controller = DockController(
        input_panel,
        decrypt_panel,
        settings_panel,
        exit_panel,
        lambda: wechat_rect(allow_overlay_foreground=not settings_panel.collapsed or not input_panel.collapsed),
    )
    controller.start()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
