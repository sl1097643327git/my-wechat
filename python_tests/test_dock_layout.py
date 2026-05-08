from wechat_overlay.dock_layout import Rect, collapsed_button_rect, chat_panel_rect, dock_areas_from_message_list, input_panel_rect, visible_wechat_rect


def test_visible_wechat_rect_removes_maximized_invisible_border():
    wechat = Rect(-8, -8, 1936, 1056)

    rect = visible_wechat_rect(wechat)

    assert rect == Rect(0, 0, 1920, 1040)


def test_visible_wechat_rect_keeps_normal_window_unchanged():
    wechat = Rect(100, 80, 1200, 900)

    rect = visible_wechat_rect(wechat)

    assert rect == wechat


def test_input_panel_tracks_bottom_right_chat_input_area():
    wechat = Rect(-8, -8, 1936, 1056)

    rect = input_panel_rect(wechat)

    assert rect.x == 576
    assert rect.y == 772
    assert rect.width == 1286
    assert rect.height == 193


def test_input_panel_matches_measured_wechat_input_area():
    wechat = Rect(351, 91, 1115, 788)
    message_list = Rect(654, 161, 809, 568)

    rect = dock_areas_from_message_list(wechat, message_list).input

    assert rect.x == 654
    assert rect.y == 729
    assert rect.width == 809
    assert rect.height == 150


def test_chat_panel_tracks_message_area_above_input():
    wechat = Rect(-8, -8, 1936, 1056)

    rect = chat_panel_rect(wechat)

    assert rect.x == 576
    assert rect.y == 83
    assert rect.width == 1286
    assert rect.height == 633


def test_chat_panel_matches_measured_wechat_message_list():
    wechat = Rect(351, 91, 1115, 788)
    message_list = Rect(654, 161, 809, 568)

    rect = dock_areas_from_message_list(wechat, message_list).chat

    assert rect.x == 654
    assert rect.y == 161
    assert rect.width == 809
    assert rect.height == 568


def test_collapsed_buttons_pin_to_wechat_right_edge():
    wechat = Rect(-8, -8, 1936, 1056)

    rect = collapsed_button_rect(wechat, y_ratio=0.8)

    visible = visible_wechat_rect(wechat)
    assert rect.x + rect.width == visible.x + visible.width - 6
    assert rect.x == 1890
    assert rect.y == 832
    assert rect.width == 24
    assert rect.height == 24


def test_collapsed_button_stays_inside_wechat_rect_when_window_has_negative_border():
    wechat = Rect(-8, -8, 1936, 1056)

    rect = collapsed_button_rect(wechat, y_ratio=0.42)

    assert rect.x >= wechat.x
    assert rect.y >= wechat.y
    assert rect.x + rect.width <= wechat.x + wechat.width
    assert rect.y + rect.height <= wechat.y + wechat.height
