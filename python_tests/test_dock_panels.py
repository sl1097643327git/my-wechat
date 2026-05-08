from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QCheckBox, QLabel, QLineEdit, QPushButton

from wechat_overlay.dock_layout import DockAreas, Rect
from wechat_overlay.dock_panels import DecryptDockWindow, ExitDockWindow, InputDockWindow, SettingsDockWindow, input_toggle_rect


def app() -> QApplication:
    existing = QApplication.instance()
    if existing is not None:
        return existing
    return QApplication([])


def test_input_panel_has_no_key_field_or_chat_mode_checkbox() -> None:
    app()
    panel = InputDockWindow(lambda *_: None, key_provider=lambda: "")

    assert panel.findChildren(QLineEdit) == []
    assert panel.findChildren(QCheckBox) == []


def test_input_decrypt_and_settings_panels_default_expanded() -> None:
    app()
    input_panel = InputDockWindow(lambda *_: None, key_provider=lambda: "key")
    decrypt_panel = DecryptDockWindow(lambda: [], key_provider=lambda: "key")
    settings_panel = SettingsDockWindow()

    assert not input_panel.collapsed
    assert not decrypt_panel.collapsed
    assert not settings_panel.collapsed


def test_input_panel_has_no_send_button_or_separate_hint_label() -> None:
    app()
    panel = InputDockWindow(lambda *_: None, key_provider=lambda: "")

    assert all(button.text() != "发送" for button in panel.findChildren(QPushButton))
    labels = [label.text() for label in panel.findChildren(QLabel)]
    assert "Enter 发送，Shift/Ctrl+Enter 换行" not in labels
    assert any("加密输入" in text and "Enter发送" in text for text in labels)


def test_decrypt_panel_does_not_own_key_or_auto_refresh_controls() -> None:
    app()
    panel = DecryptDockWindow(lambda: [], key_provider=lambda: "key")

    assert panel.findChildren(QLineEdit) == []
    assert panel.findChildren(QCheckBox) == []


def test_decrypt_panel_warns_when_refresh_without_key() -> None:
    app()
    panel = DecryptDockWindow(lambda: [], key_provider=lambda: "")

    panel.refresh()

    assert panel.status.text() == "请先填写统一密钥"


class OverlayShowProbe:
    def __init__(self) -> None:
        self.show_calls = 0
        self.rendered = []

    def render_messages(self, messages) -> None:
        self.rendered.append(messages)

    def show(self) -> None:
        self.show_calls += 1

    def isVisible(self) -> bool:
        return True

    def follow(self, x, y, width, height) -> None:
        self.follow_args = (x, y, width, height)


def test_decrypt_panel_refresh_does_not_show_already_visible_overlay() -> None:
    app()
    panel = DecryptDockWindow(lambda: [], key_provider=lambda: "key")
    probe = OverlayShowProbe()
    panel.overlay = probe

    panel.refresh()

    assert probe.show_calls == 0


def test_decrypt_panel_refresh_initializes_overlay_geometry_before_rendering() -> None:
    app()
    panel = DecryptDockWindow(lambda: [object()], key_provider=lambda: "key")
    probe = OverlayShowProbe()
    panel.overlay = probe
    areas = DockAreas(Rect(100, 100, 900, 700), Rect(300, 160, 650, 400), Rect(300, 560, 650, 140))
    panel.apply_geometry(areas)

    panel.overlay.follow_args = None
    panel.refresh()

    assert probe.follow_args == (300, 160, 650, 400)


def test_settings_panel_owns_key_and_auto_refresh_controls() -> None:
    app()
    panel = SettingsDockWindow()

    assert panel.key_provider() == ""
    assert panel.key_input.placeholderText() == "统一密钥"
    assert not panel.auto_refresh_checkbox.isChecked()
    assert panel.interval_input.text() == "1000"
    assert panel.auto_refresh_interval_ms() == 1000


def test_settings_panel_key_input_has_eye_toggle_button() -> None:
    app()
    panel = SettingsDockWindow()

    assert panel.key_input.echoMode() == QLineEdit.EchoMode.Password
    assert panel.key_visibility_button.text() == "👁"
    assert panel.key_visibility_button.toolTip() == "显示密钥"


def test_settings_panel_eye_button_toggles_key_visibility() -> None:
    app()
    panel = SettingsDockWindow()

    panel.key_visibility_button.click()

    assert panel.key_input.echoMode() == QLineEdit.EchoMode.Normal
    assert panel.key_visibility_button.text() == "🙈"
    assert panel.key_visibility_button.toolTip() == "隐藏密钥"

    panel.key_visibility_button.click()

    assert panel.key_input.echoMode() == QLineEdit.EchoMode.Password
    assert panel.key_visibility_button.text() == "👁"
    assert panel.key_visibility_button.toolTip() == "显示密钥"


def test_settings_panel_accepts_focus_for_text_inputs() -> None:
    app()
    panel = SettingsDockWindow()

    assert not panel.windowFlags() & Qt.WindowType.WindowDoesNotAcceptFocus


def test_settings_panel_reports_active_text_input_when_expanded() -> None:
    app()
    panel = SettingsDockWindow()

    assert panel.has_active_text_input()


def test_input_panel_reports_active_text_input_when_expanded() -> None:
    app()
    panel = InputDockWindow(lambda *_: None, key_provider=lambda: "key")

    assert panel.has_active_text_input()


def test_settings_panel_clamps_interval_to_500ms() -> None:
    app()
    panel = SettingsDockWindow()

    panel.interval_input.setText("100")

    assert panel.auto_refresh_interval_ms() == 500


def test_decrypt_panel_has_round_small_exit_button() -> None:
    app()
    panel = ExitDockWindow()

    assert panel.exit_button.text() == "×"
    assert panel.exit_button.width() <= 28
    assert "border-radius" in panel.exit_button.styleSheet()


def test_input_and_decrypt_panels_do_not_own_exit_buttons() -> None:
    app()
    input_panel = InputDockWindow(lambda *_: None, key_provider=lambda: "")
    decrypt_panel = DecryptDockWindow(lambda: [], key_provider=lambda: "key")

    assert all(button.text() not in {"退出", "×"} for button in input_panel.findChildren(QPushButton))
    assert all(button.text() not in {"退出", "×"} for button in decrypt_panel.findChildren(QPushButton))


def test_decrypt_panel_uses_icon_refresh_and_visible_collapse_icon() -> None:
    app()
    panel = DecryptDockWindow(lambda: [], key_provider=lambda: "key")

    texts = [button.text() for button in panel.findChildren(QPushButton)]
    assert "刷新" not in texts
    assert "↻" in texts
    assert panel.collapse_button.text() == ">"
    assert panel.collapse_button.width() >= 24


def test_decrypt_panel_has_no_title_or_status_copy() -> None:
    app()
    panel = DecryptDockWindow(lambda: [], key_provider=lambda: "key")

    labels = [label.text() for label in panel.findChildren(QLabel)]
    assert "👁 解密蒙层" not in labels
    assert "点击刷新显示解密气泡" not in labels


def test_input_collapse_button_floats_inside_text_area_top_right() -> None:
    app()
    panel = InputDockWindow(lambda *_: None, key_provider=lambda: "key")
    areas = DockAreas(Rect(100, 100, 900, 700), Rect(300, 160, 650, 400), Rect(300, 560, 650, 140))
    panel.collapsed = False
    panel.apply_geometry(areas)

    assert panel.collapse_button.parent() is panel.text_input
    assert panel.collapse_button.geometry().x() == panel.text_input.width() - 30
    assert panel.collapse_button.geometry().y() == 6


def test_input_collapsed_button_matches_expanded_collapse_screen_position() -> None:
    app()
    panel = InputDockWindow(lambda *_: None, key_provider=lambda: "key")
    areas = DockAreas(Rect(100, 100, 900, 700), Rect(300, 160, 650, 400), Rect(300, 560, 650, 140))

    panel.collapsed = True
    panel.apply_geometry(areas)

    expected = input_toggle_rect(areas.input)
    assert panel.geometry().x() == expected.x
    assert panel.geometry().y() == expected.y


def test_decrypt_panel_has_dedicated_border_frame() -> None:
    app()
    panel = DecryptDockWindow(lambda: [], key_provider=lambda: "key")

    assert "border: 2px solid" in panel.border_frame.styleSheet()


def test_settings_ms_label_has_no_orange_border() -> None:
    app()
    panel = SettingsDockWindow()

    assert "border: none" in panel.ms_label.styleSheet()


def test_input_panel_sends_using_external_key_provider_to_current_chat() -> None:
    app()
    sends: list[tuple[str, str, bool]] = []
    panel = InputDockWindow(lambda key, text, current: sends.append((key, text, current)), key_provider=lambda: "shared-key")
    panel.text_input.setPlainText("hello")

    panel._send()

    assert sends == [("shared-key", "hello", True)]


def test_input_panel_clears_and_refocuses_after_send() -> None:
    qt_app = app()
    panel = InputDockWindow(lambda *_: None, key_provider=lambda: "shared-key")
    panel.collapsed = False
    panel.show()
    panel.text_input.setPlainText("hello")

    panel._send()
    qt_app.processEvents()

    assert panel.text_input.toPlainText() == ""
    assert panel.text_input.hasFocus()
