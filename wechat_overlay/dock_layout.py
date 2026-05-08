from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class DockAreas:
    wechat: Rect
    chat: Rect
    input: Rect


def visible_wechat_rect(wechat: Rect) -> Rect:
    """Trim the invisible resize frame reported by maximized Windows windows."""
    left = max(wechat.x, 0)
    top = max(wechat.y, 0)
    right = wechat.x + wechat.width
    bottom = wechat.y + wechat.height
    if wechat.x < 0:
        right += wechat.x
    if wechat.y < 0:
        bottom += wechat.y
    return Rect(left, top, max(0, right - left), max(0, bottom - top))


def dock_areas_from_message_list(wechat: Rect, message_list: Rect | None) -> DockAreas:
    visible = visible_wechat_rect(wechat)
    if message_list is None:
        return DockAreas(visible, chat_panel_rect(visible), input_panel_rect(visible))
    input_top = message_list.y + message_list.height
    return DockAreas(
        wechat=visible,
        chat=message_list,
        input=Rect(message_list.x, input_top, message_list.width, max(0, visible.y + visible.height - input_top)),
    )


def chat_panel_rect(wechat: Rect) -> Rect:
    wechat = visible_wechat_rect(wechat)
    main_x = wechat.x + round(wechat.width * 0.30)
    top = wechat.y + round(wechat.height * 0.08)
    bottom = wechat.y + int(wechat.height * 0.689)
    return Rect(
        x=main_x,
        y=top,
        width=round(wechat.width * 0.67),
        height=bottom - top,
    )


def input_panel_rect(wechat: Rect) -> Rect:
    wechat = visible_wechat_rect(wechat)
    main_x = wechat.x + round(wechat.width * 0.30)
    top = wechat.y + round(wechat.height * 0.742)
    bottom = wechat.y + round(wechat.height * 0.928)
    return Rect(
        x=main_x,
        y=top,
        width=round(wechat.width * 0.67),
        height=bottom - top,
    )


def settings_panel_rect(wechat: Rect) -> Rect:
    wechat = visible_wechat_rect(wechat)
    width = min(620, max(320, round(wechat.width * 0.42)))
    return Rect(
        x=wechat.x + round((wechat.width - width) / 2),
        y=wechat.y + 8,
        width=width,
        height=74,
    )


def collapsed_button_rect(wechat: Rect, *, y_ratio: float) -> Rect:
    wechat = visible_wechat_rect(wechat)
    width = 24
    height = 24
    inner_margin = 6
    return Rect(
        x=wechat.x + wechat.width - inner_margin - width,
        y=wechat.y + int(wechat.height * y_ratio),
        width=width,
        height=height,
    )
