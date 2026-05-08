from wechat_overlay.dock_style import collapsed_label, expanded_label, overlay_message_stylesheet, panel_stylesheet


def test_dock_labels_change_between_collapsed_and_expanded():
    assert collapsed_label("加密") == "‹"
    assert collapsed_label("解密") == "‹"
    assert expanded_label() == ">"


def test_overlay_styles_use_dark_text_and_visible_background():
    style = overlay_message_stylesheet()

    assert "color: #111827" in style
    assert "rgba(255, 214, 102" in style


def test_panel_style_has_visible_background_and_dark_text():
    style = panel_stylesheet()

    assert "background: rgba(255, 248, 220" in style
    assert "color: #111827" in style
