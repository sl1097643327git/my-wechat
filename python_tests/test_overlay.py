from unittest.mock import patch

from PySide6.QtCore import QRect

from PySide6.QtWidgets import QApplication

from wechat_overlay.overlay import OverlayMessage, OverlayWindow, adaptive_bubble_rect, choose_bubble_size, overlay_bubble_max_width


def app() -> QApplication:
    existing = QApplication.instance()
    if existing is not None:
        return existing
    return QApplication([])


def test_adaptive_bubble_rect_uses_plaintext_content_size() -> None:
    message = OverlayMessage("短消息", 100, 80, 300, 90)
    rect = adaptive_bubble_rect(message, QRect(0, 0, 600, 400), 72, 34)

    assert rect.width == 72
    assert rect.height == 34


def test_adaptive_bubble_rect_left_side_uses_overlay_left_edge() -> None:
    message = OverlayMessage("短消息", 220, 80, 300, 90)
    rect = adaptive_bubble_rect(message, QRect(100, 40, 600, 400), 72, 34)

    assert rect.x == 180


def test_adaptive_bubble_rect_right_side_uses_overlay_right_edge() -> None:
    message = OverlayMessage("me", 420, 80, 120, 60, side="right")
    rect = adaptive_bubble_rect(message, QRect(0, 0, 600, 400), 80, 32)

    assert rect.x + rect.width == 520


def test_adaptive_bubble_rect_left_side_uses_overlay_left_edge_without_window_offset() -> None:
    message = OverlayMessage("friend", 60, 80, 160, 60)
    rect = adaptive_bubble_rect(message, QRect(0, 0, 600, 400), 90, 32)

    assert rect.x == 80


def test_adaptive_bubble_rect_stays_inside_overlay() -> None:
    message = OverlayMessage("edge", 570, 390, 90, 60)
    rect = adaptive_bubble_rect(message, QRect(0, 0, 600, 400), 120, 40)

    assert rect.x + rect.width <= 600
    assert rect.y + rect.height <= 400


def test_overlay_bubble_max_width_uses_45_percent_of_chat_width() -> None:
    assert overlay_bubble_max_width(1000) == 900


def test_overlay_bubble_max_width_has_minimum_for_narrow_chat() -> None:
    assert overlay_bubble_max_width(60) == 80


def test_choose_bubble_size_keeps_short_content_narrow_when_it_fits_original_height() -> None:
    size = choose_bubble_size(min_width=80, max_width=400, original_height=80, height_for_width=lambda width: 40)

    assert size.width == 80
    assert size.height == 40
    assert not size.collapsed


def test_choose_bubble_size_expands_width_until_content_fits_original_height() -> None:
    size = choose_bubble_size(min_width=80, max_width=400, original_height=80, height_for_width=lambda width: 120 if width < 240 else 70)

    assert size.width == 240
    assert size.height == 70
    assert not size.collapsed


def test_choose_bubble_size_collapses_when_max_width_still_exceeds_original_height() -> None:
    size = choose_bubble_size(min_width=80, max_width=400, original_height=80, height_for_width=lambda width: 140)

    assert size.width == 400
    assert size.height == 80
    assert size.full_height == 140
    assert size.collapsed


def test_overlay_window_expands_only_one_collapsed_bubble_at_a_time() -> None:
    app()
    overlay = OverlayWindow()
    overlay.follow(0, 0, 800, 500)
    messages = [
        OverlayMessage("长内容" * 120, 80, 80, 200, 36),
        OverlayMessage("另一条长内容" * 120, 80, 160, 200, 36),
    ]
    overlay.render_messages(messages)

    first, second = overlay._labels
    first.mousePressEvent(None)
    assert first.property("expanded") is True

    second.mousePressEvent(None)
    assert first.property("expanded") is False
    assert second.property("expanded") is True


def test_copy_icon_sits_on_right_side_for_left_bubble() -> None:
    app()
    overlay = OverlayWindow()
    overlay.follow(0, 0, 800, 500)
    overlay.show()
    overlay.render_messages([OverlayMessage("copy me", 80, 80, 200, 60, side="left")])

    bubble = overlay._labels[0]
    copy_button = overlay._copy_buttons[0]

    assert copy_button.geometry().x() >= bubble.geometry().x() + bubble.geometry().width()


def test_copy_icon_sits_on_left_side_for_right_bubble() -> None:
    app()
    overlay = OverlayWindow()
    overlay.follow(0, 0, 800, 500)
    overlay.render_messages([OverlayMessage("copy me", 520, 80, 200, 60, side="right")])

    bubble = overlay._labels[0]
    copy_button = overlay._copy_buttons[0]

    assert copy_button.geometry().x() + copy_button.geometry().width() <= bubble.geometry().x()


def test_copy_icon_copies_plaintext_to_clipboard() -> None:
    app()
    overlay = OverlayWindow()
    overlay.follow(0, 0, 800, 500)
    overlay.render_messages([OverlayMessage("copy me", 80, 80, 200, 60, side="left")])

    overlay._copy_text("copy me")

    assert overlay._last_copied_text == "copy me"


def test_copy_text_writes_system_clipboard() -> None:
    app()
    overlay = OverlayWindow()

    with patch("wechat_overlay.overlay.pyperclip.copy") as copy:
        overlay._copy_text("copy me")

    copy.assert_called_once_with("copy me")


def test_copy_icon_shows_transient_success_popup() -> None:
    app()
    overlay = OverlayWindow()
    overlay.follow(0, 0, 800, 500)
    overlay.show()
    overlay.render_messages([OverlayMessage("copy me", 80, 80, 200, 60, side="left")])

    overlay._copy_buttons[0].click()

    assert overlay._copy_popup is not None
    assert overlay._copy_popup.text() == "复制成功"
    assert overlay._copy_popup.isVisible()


def test_copy_success_popup_is_centered_on_screen_geometry() -> None:
    app()
    overlay = OverlayWindow()
    screen = QRect(0, 0, 1200, 800)
    overlay.follow(100, 100, 400, 300)

    rect = overlay.copy_popup_rect(screen, 120, 40)

    assert rect.x() == 540
    assert rect.y() == 380


def test_expanded_bubble_state_survives_refresh_for_same_message() -> None:
    app()
    overlay = OverlayWindow()
    overlay.follow(0, 0, 800, 500)
    message = OverlayMessage("长内容" * 120, 80, 80, 200, 36)
    overlay.render_messages([message])
    overlay._labels[0].mousePressEvent(None)
    assert overlay._labels[0].property("expanded") is True


def test_render_messages_reuses_existing_label_for_same_message_to_avoid_flicker() -> None:
    app()
    overlay = OverlayWindow()
    overlay.follow(0, 0, 800, 500)
    message = OverlayMessage("稳定内容", 80, 80, 200, 60)
    overlay.render_messages([message])
    first_label = overlay._labels[0]

    overlay.render_messages([message])

    assert overlay._labels[0] is first_label


def test_copy_button_has_pressed_visual_effect_style() -> None:
    app()
    overlay = OverlayWindow()
    overlay.follow(0, 0, 800, 500)
    overlay.render_messages([OverlayMessage("copy me", 80, 80, 200, 60, side="left")])

    assert "QPushButton:pressed" in overlay._copy_buttons[0].styleSheet()


def test_copy_button_moves_down_while_pressed_and_returns_on_release() -> None:
    app()
    overlay = OverlayWindow()
    overlay.follow(0, 0, 800, 500)
    overlay.render_messages([OverlayMessage("copy me", 80, 80, 200, 60, side="left")])
    button = overlay._copy_buttons[0]
    rest = button.geometry()

    overlay._press_copy_button(button)

    assert button.geometry().x() == rest.x() + 2
    assert button.geometry().y() == rest.y() + 2

    overlay._release_copy_button(button)

    assert button.geometry() == rest
