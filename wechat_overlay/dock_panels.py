from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QCheckBox, QHBoxLayout, QLabel, QLineEdit, QPushButton, QSizePolicy, QVBoxLayout, QWidget

from wechat_overlay.dock_layout import DockAreas, Rect, chat_panel_rect, collapsed_button_rect, input_panel_rect, settings_panel_rect
from wechat_overlay.dock_style import collapsed_button_stylesheet, collapsed_label, expanded_label, panel_stylesheet
from wechat_overlay.overlay import OverlayMessage, OverlayWindow
from wechat_overlay.widgets import PlaintextEditor


def input_toggle_rect(input_rect: Rect) -> Rect:
    layout_margin = 9
    layout_spacing = 6
    title_height = 24
    text_input_top = input_rect.y + layout_margin + title_height + layout_spacing
    return Rect(input_rect.x + input_rect.width - layout_margin - 30, text_input_top + 6, 24, 24)


class DockWindow(QWidget):
    def __init__(self, expanded_title: str, collapsed_title: str, *, accepts_focus: bool = True) -> None:
        super().__init__()
        self.expanded_title = expanded_title
        self.collapsed_title = collapsed_title
        self.collapsed = False
        self._last_wechat_rect: Rect | None = None
        flags = Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool
        if not accepts_focus:
            flags |= Qt.WindowType.WindowDoesNotAcceptFocus
        self.setWindowFlags(flags)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet(panel_stylesheet())
        self._collapsed_children: list[QWidget] = []
        self._expanded_children: list[QWidget] = []

    def toggle_collapsed(self) -> None:
        self.collapsed = not self.collapsed
        self.update_button_labels()
        if self._last_wechat_rect is not None:
            self.apply_geometry(getattr(self, "_last_dock_areas", self._last_wechat_rect))

    def set_collapsed_mode(self, rect: Rect) -> None:
        for child in self._expanded_children:
            child.hide()
        for child in self._collapsed_children:
            child.show()
        if self.layout() is not None:
            self.layout().setContentsMargins(0, 0, 0, 0)
            self.layout().setSpacing(0)
        self.resize(rect.width, rect.height)
        self.setGeometry(rect.x, rect.y, rect.width, rect.height)
        self.setFixedSize(rect.width, rect.height)

    def set_expanded_mode(self, rect: Rect) -> None:
        self.setMaximumSize(16777215, 16777215)
        self.setMinimumSize(0, 0)
        if self.layout() is not None:
            self.layout().setContentsMargins(9, 9, 9, 9)
            self.layout().setSpacing(6)
        self.setGeometry(rect.x, rect.y, rect.width, rect.height)
        self.setFixedSize(rect.width, rect.height)
        for child in self._collapsed_children:
            child.hide()
        for child in self._expanded_children:
            child.show()

    def force_expanded_size(self, rect: Rect) -> None:
        self.setFixedSize(rect.width, rect.height)
        self.setGeometry(rect.x, rect.y, rect.width, rect.height)

    def update_button_labels(self) -> None:
        pass


class InputDockWindow(DockWindow):
    def __init__(self, on_send: Callable[[str, str, bool], None], key_provider: Callable[[], str]) -> None:
        super().__init__("加密输入", "加密")
        self._on_send = on_send
        self._key_provider = key_provider
        self.text_input = PlaintextEditor(self._send)
        self.toggle_button = QPushButton(collapsed_label("加密"))
        self.toggle_button.setToolTip("展开加密输入")
        self.toggle_button.setStyleSheet(collapsed_button_stylesheet())
        self.toggle_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.toggle_button.clicked.connect(self.toggle_collapsed)
        self._build_layout()
        self._collapsed_children = [self.toggle_button]
        self._expanded_children = [self.collapse_button, self.title, self.text_input]

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(self.toggle_button)
        header = QHBoxLayout()
        self.title = QLabel("🔐 加密输入 · Enter发送，Shift/Ctrl+Enter换行")
        self.collapse_button = QPushButton(expanded_label())
        self.collapse_button.setFixedSize(24, 24)
        self.collapse_button.setStyleSheet(collapsed_button_stylesheet())
        collapse = self.collapse_button
        collapse.clicked.connect(self.toggle_collapsed)
        header.addSpacing(190)
        header.addWidget(self.title)
        header.addStretch()
        layout.addLayout(header)
        layout.addWidget(self.text_input)
        self.collapse_button.setParent(self.text_input)

    def apply_geometry(self, wechat_rect: Rect | DockAreas) -> None:
        areas = wechat_rect if isinstance(wechat_rect, DockAreas) else DockAreas(wechat_rect, chat_panel_rect(wechat_rect), input_panel_rect(wechat_rect))
        self._last_dock_areas = areas
        self._last_wechat_rect = areas.wechat
        rect = input_toggle_rect(areas.input) if self.collapsed else areas.input
        if self.collapsed:
            self.set_collapsed_mode(rect)
        else:
            self.set_expanded_mode(rect)
            self.force_expanded_size(rect)
        self.toggle_button.setFixedSize(rect.width, rect.height)
        self.toggle_button.setGeometry(0, 0, rect.width, rect.height)
        self.toggle_button.raise_()
        if not self.collapsed and hasattr(self, "collapse_button"):
            self.collapse_button.setGeometry(self.text_input.width() - 30, 6, 24, 24)
            self.collapse_button.raise_()
        self.update_button_labels()

    def update_button_labels(self) -> None:
        self.toggle_button.setText(collapsed_label("加密"))
        if hasattr(self, "collapse_button"):
            self.collapse_button.setText(expanded_label())

    def _send(self) -> None:
        text = self.text_input.toPlainText().strip()
        if not text:
            self.text_input.setFocus(Qt.FocusReason.OtherFocusReason)
            return
        self._on_send(self._key_provider(), text, True)
        self.text_input.clear()
        self.raise_()
        self.activateWindow()
        self.text_input.setFocus(Qt.FocusReason.OtherFocusReason)

    def has_active_text_input(self) -> bool:
        return not self.collapsed


class SettingsDockWindow(DockWindow):
    def __init__(self) -> None:
        super().__init__("设置", "设置")
        self.key_input = QLineEdit()
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_input.setPlaceholderText("统一密钥")
        self.key_input.setFixedHeight(30)
        self.key_visibility_button = QPushButton("👁")
        self.key_visibility_button.setFixedSize(28, 30)
        self.key_visibility_button.setToolTip("显示密钥")
        self.key_visibility_button.setStyleSheet("QPushButton { border: none; background: rgba(255,255,255,245); border-radius: 6px; padding: 0; font-size: 14px; } QPushButton:pressed { background: rgba(245,158,11,220); }")
        self.key_visibility_button.clicked.connect(self.toggle_key_visibility)
        self.auto_refresh_checkbox = QCheckBox("自动刷新")
        self.auto_refresh_checkbox.setChecked(False)
        self.auto_refresh_checkbox.setStyleSheet("QCheckBox { border: none; background: transparent; }")
        self.interval_input = QLineEdit("1000")
        self.interval_input.setFixedWidth(58)
        self.interval_input.setStyleSheet("QLineEdit { border: none; background: rgba(255,255,255,245); border-radius: 6px; padding: 4px 6px; }")
        self.toggle_button = QPushButton("⚙")
        self.toggle_button.setToolTip("展开设置")
        self.toggle_button.setStyleSheet(collapsed_button_stylesheet())
        self.toggle_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.toggle_button.clicked.connect(self.toggle_collapsed)
        self._build_layout()
        self._collapsed_children = [self.toggle_button]
        self._expanded_children = [self.key_input, self.key_visibility_button, self.auto_refresh_checkbox, self.interval_input, self.collapse_button]

    def _build_layout(self) -> None:
        layout = QHBoxLayout(self)
        layout.addWidget(self.toggle_button)
        layout.addWidget(self.key_input)
        layout.addWidget(self.key_visibility_button)
        layout.addWidget(self.auto_refresh_checkbox)
        layout.addWidget(self.interval_input)
        self.ms_label = QLabel("ms")
        self.ms_label.setStyleSheet("QLabel { border: none; background: transparent; }")
        layout.addWidget(self.ms_label)
        self.collapse_button = QPushButton(expanded_label())
        self.collapse_button.setFixedSize(24, 24)
        self.collapse_button.setStyleSheet(collapsed_button_stylesheet())
        self.collapse_button.clicked.connect(self.toggle_collapsed)
        layout.addWidget(self.collapse_button)

    def key_provider(self) -> str:
        return self.key_input.text()

    def set_key(self, key: str) -> None:
        self.key_input.setText(key)

    def set_key_changed_handler(self, handler: Callable[[str], None]) -> None:
        self.key_input.textChanged.connect(handler)

    def toggle_key_visibility(self) -> None:
        if self.key_input.echoMode() == QLineEdit.EchoMode.Password:
            self.key_input.setEchoMode(QLineEdit.EchoMode.Normal)
            self.key_visibility_button.setText("🙈")
            self.key_visibility_button.setToolTip("隐藏密钥")
            return
        self.key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_visibility_button.setText("👁")
        self.key_visibility_button.setToolTip("显示密钥")

    def has_active_text_input(self) -> bool:
        return not self.collapsed

    def auto_refresh_interval_ms(self) -> int:
        try:
            return max(500, int(self.interval_input.text()))
        except ValueError:
            return 1000

    def apply_geometry(self, wechat_rect: Rect | DockAreas) -> None:
        areas = wechat_rect if isinstance(wechat_rect, DockAreas) else DockAreas(wechat_rect, chat_panel_rect(wechat_rect), input_panel_rect(wechat_rect))
        self._last_dock_areas = areas
        self._last_wechat_rect = areas.wechat
        rect = collapsed_button_rect(areas.wechat, y_ratio=0.12) if self.collapsed else settings_panel_rect(areas.wechat)
        if self.collapsed:
            self.set_collapsed_mode(rect)
        else:
            self.set_expanded_mode(rect)
            self.force_expanded_size(rect)
        self.toggle_button.setFixedSize(rect.width, rect.height)
        self.toggle_button.setGeometry(0, 0, rect.width, rect.height)
        self.toggle_button.raise_()


class ExitDockWindow(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.exit_button = QPushButton("×", self)
        self.exit_button.setFixedSize(24, 24)
        self.exit_button.setStyleSheet("QPushButton { background: rgba(245, 158, 11, 245); border-radius: 12px; padding: 0; font-weight: 900; }")
        self.exit_button.clicked.connect(QApplication.quit)
        self.setFixedSize(24, 24)

    def apply_geometry(self, wechat_rect: Rect | DockAreas) -> None:
        areas = wechat_rect if isinstance(wechat_rect, DockAreas) else DockAreas(wechat_rect, chat_panel_rect(wechat_rect), input_panel_rect(wechat_rect))
        settings_button = collapsed_button_rect(areas.wechat, y_ratio=0.12)
        self.setGeometry(settings_button.x, settings_button.y - 28, 24, 24)
        self.exit_button.setGeometry(0, 0, 24, 24)


class DecryptDockWindow(DockWindow):
    def __init__(self, on_refresh: Callable[[], list[OverlayMessage]], key_provider: Callable[[], str]) -> None:
        super().__init__("解密蒙层", "解密", accepts_focus=False)
        self._on_refresh = on_refresh
        self._key_provider = key_provider
        self.overlay = OverlayWindow()
        self.border_frame = QWidget(self)
        self.border_frame.setStyleSheet("QWidget { background: transparent; border: 2px solid rgba(217, 119, 6, 230); border-radius: 14px; }")
        self.status = QLabel("")
        self.refresh_button = QPushButton("↻")
        self.refresh_button.setFixedSize(24, 24)
        self.refresh_button.setToolTip("刷新")
        self.refresh_button.setStyleSheet(collapsed_button_stylesheet())
        self.refresh_button.clicked.connect(self.refresh)
        self.toggle_button = QPushButton(collapsed_label("解密"))
        self.toggle_button.setToolTip("展开解密蒙层")
        self.toggle_button.setStyleSheet(collapsed_button_stylesheet())
        self.toggle_button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.toggle_button.clicked.connect(self.toggle_collapsed)
        self._build_layout()
        self._collapsed_children = [self.toggle_button]
        self._expanded_children = [self.collapse_button]

    def _build_layout(self) -> None:
        layout = QVBoxLayout(self)
        layout.addWidget(self.toggle_button)
        controls = QHBoxLayout()
        self.collapse_button = QPushButton(expanded_label())
        self.collapse_button.setFixedSize(24, 24)
        self.collapse_button.setStyleSheet(collapsed_button_stylesheet())
        collapse = self.collapse_button
        collapse.clicked.connect(self.toggle_collapsed)
        controls.addStretch()
        controls.addWidget(self.refresh_button)
        controls.addWidget(collapse)
        layout.addLayout(controls)
        layout.addStretch()

    def apply_geometry(self, wechat_rect: Rect | DockAreas) -> None:
        areas = wechat_rect if isinstance(wechat_rect, DockAreas) else DockAreas(wechat_rect, chat_panel_rect(wechat_rect), input_panel_rect(wechat_rect))
        self._last_dock_areas = areas
        self._last_wechat_rect = areas.wechat
        panel = areas.chat
        rect = collapsed_button_rect(areas.wechat, y_ratio=0.42) if self.collapsed else panel
        if self.collapsed:
            self.set_collapsed_mode(rect)
            self.refresh_button.hide()
            self.border_frame.hide()
        else:
            self.set_expanded_mode(rect)
            self.force_expanded_size(rect)
            self.border_frame.setGeometry(0, 0, rect.width, rect.height)
            self.border_frame.show()
            self.border_frame.lower()
            self.refresh_button.show()
        self.overlay.follow(panel.x, panel.y, panel.width, panel.height)
        self.toggle_button.setFixedSize(rect.width, rect.height)
        self.toggle_button.setGeometry(0, 0, rect.width, rect.height)
        self.toggle_button.raise_()
        self.update_button_labels()
        if self.collapsed:
            self.overlay.hide()

    def update_button_labels(self) -> None:
        self.toggle_button.setText(collapsed_label("解密"))
        if hasattr(self, "collapse_button"):
            self.collapse_button.setText(expanded_label())

    def refresh(self) -> None:
        if not self._key_provider().strip():
            self.status.setText("请先填写统一密钥")
            return
        if hasattr(self, "_last_dock_areas"):
            areas = self._last_dock_areas
            self.overlay.follow(areas.chat.x, areas.chat.y, areas.chat.width, areas.chat.height)
        messages = self._on_refresh()
        self.overlay.render_messages(messages)
        if not self.collapsed and not self.overlay.isVisible():
            self.overlay.show()
        self.status.setText(f"已显示 {len(messages)} 条解密消息")


class DockController:
    def __init__(self, input_panel: InputDockWindow, decrypt_panel: DecryptDockWindow, settings_panel: SettingsDockWindow, exit_panel: ExitDockWindow, get_wechat_rect: Callable[[], Rect | DockAreas | None]) -> None:
        self.input_panel = input_panel
        self.decrypt_panel = decrypt_panel
        self.settings_panel = settings_panel
        self.exit_panel = exit_panel
        self._get_wechat_rect = get_wechat_rect
        self.timer = QTimer()
        self.timer.timeout.connect(self.tick)
        self.auto_refresh_timer = QTimer()
        self.auto_refresh_timer.timeout.connect(self.auto_refresh)

    def start(self) -> None:
        self.input_panel.show()
        self.decrypt_panel.show()
        self.settings_panel.show()
        self.exit_panel.show()
        self.timer.start(120)
        self.auto_refresh_timer.start(1000)
        self.tick()

    def auto_refresh(self) -> None:
        if self.settings_panel.auto_refresh_checkbox.isChecked() and self.input_panel.isVisible() and not self.decrypt_panel.collapsed:
            self.decrypt_panel.refresh()
        interval = self.settings_panel.auto_refresh_interval_ms()
        if self.auto_refresh_timer.interval() != interval:
            self.auto_refresh_timer.start(interval)

    def tick(self) -> None:
        rect = self._get_wechat_rect()
        if rect is None:
            self.input_panel.hide()
            self.decrypt_panel.hide()
            self.settings_panel.hide()
            self.exit_panel.hide()
            self.decrypt_panel.overlay.hide()
            return
        self.input_panel.show()
        self.decrypt_panel.show()
        self.settings_panel.show()
        self.exit_panel.show()
        last_rect = rect.wechat if isinstance(rect, DockAreas) else rect
        if last_rect != self.input_panel._last_wechat_rect:
            self.input_panel.apply_geometry(rect)
            self.decrypt_panel.apply_geometry(rect)
            self.settings_panel.apply_geometry(rect)
            self.exit_panel.apply_geometry(rect)
