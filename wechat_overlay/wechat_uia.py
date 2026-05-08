from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Iterable

import pyperclip
import psutil
from pywinauto import Desktop
from pywinauto.application import Application
from pywinauto.controls.uiawrapper import UIAWrapper

from wechat_overlay.dock_layout import Rect


WECHAT_PROCESS_NAMES = {"weixin", "wechat", "wechatappex"}
FILE_TRANSFER_ASSISTANT = "文件传输助手"


class SendSafetyError(RuntimeError):
    """Raised when a send action could target the wrong chat."""


@dataclass(frozen=True)
class WechatWindow:
    wrapper: UIAWrapper
    title: str
    process_id: int


def is_wechat_process_name(process_name: str) -> bool:
    return process_name.lower() in WECHAT_PROCESS_NAMES


def contains_file_transfer_assistant(texts: Iterable[str]) -> bool:
    return any(FILE_TRANSFER_ASSISTANT in text for text in texts)


def require_file_transfer(texts: Iterable[str]) -> None:
    if not contains_file_transfer_assistant(texts):
        raise SendSafetyError("文件传输助手未在当前微信窗口中可见，拒绝发送。")


def find_wechat_window() -> WechatWindow | None:
    desktop = Desktop(backend="uia")
    for window in desktop.windows():
        try:
            process_id = window.process_id()
            process_name = _process_name(process_id)
            title = window.window_text()
        except Exception:
            continue

        if is_wechat_process_name(process_name):
            return WechatWindow(wrapper=window, title=title, process_id=process_id)
    return None


class WechatWindowCache:
    def __init__(self) -> None:
        self._window: WechatWindow | None = None

    def get(self) -> WechatWindow | None:
        if self._window is not None and _is_wrapper_alive(self._window.wrapper):
            return self._window
        self._window = find_wechat_window()
        return self._window


def visible_texts(window: WechatWindow, limit: int = 500) -> list[str]:
    texts: list[str] = []
    for control in window.wrapper.descendants():
        if len(texts) >= limit:
            break
        try:
            text = control.window_text().strip()
        except Exception:
            continue
        if text:
            texts.append(text)
    return texts


def is_file_transfer_visible(window: WechatWindow) -> bool:
    return contains_file_transfer_assistant(visible_texts(window))


def should_show_overlay(wechat_pid: int | None, foreground_pid: int | None) -> bool:
    return wechat_pid is not None and foreground_pid == wechat_pid


def foreground_process_id() -> int | None:
    try:
        window = Application().connect(active_only=True).top_window()
        return window.process_id()
    except Exception:
        return None


def message_list_rect(window: WechatWindow) -> Rect | None:
    for control in window.wrapper.descendants():
        try:
            if control.friendly_class_name() != "ListBox":
                continue
            text = control.window_text().strip()
            if text != "消息":
                continue
            rect = control.rectangle()
            return Rect(rect.left, rect.top, rect.width(), rect.height())
        except Exception:
            continue
    return None


def send_text(window: WechatWindow, text: str) -> bool:
    if not text:
        return False

    window.wrapper.set_focus()
    time.sleep(0.2)
    previous_clipboard = _safe_clipboard_get()
    pyperclip.copy(text)
    window.wrapper.type_keys("^v", set_foreground=True)
    time.sleep(0.1)
    window.wrapper.type_keys("{ENTER}", set_foreground=True)
    if previous_clipboard is not None:
        pyperclip.copy(previous_clipboard)
    return True


def send_text_to_file_transfer(window: WechatWindow, text: str) -> bool:
    require_file_transfer(visible_texts(window))
    return send_text(window, text)


def send_text_to_current_chat(window: WechatWindow, text: str) -> bool:
    """Send to the currently open chat. Caller must ensure the chat is correct."""
    return send_text(window, text)


def _process_name(process_id: int) -> str:
    return psutil.Process(process_id).name().rsplit(".", 1)[0]


def _is_wrapper_alive(wrapper: UIAWrapper) -> bool:
    try:
        _ = wrapper.rectangle()
        return True
    except Exception:
        return False


def _safe_clipboard_get() -> str | None:
    try:
        return pyperclip.paste()
    except pyperclip.PyperclipException:
        return None
