from types import SimpleNamespace
from unittest.mock import patch

from PIL import Image

from wechat_overlay import app as overlay_app
from wechat_overlay.dock_layout import DockAreas, Rect


class VisibleOverlayProbe:
    def __init__(self) -> None:
        self.hide_calls = 0
        self.show_calls = 0

    def isVisible(self) -> bool:
        return True

    def hide(self) -> None:
        self.hide_calls += 1

    def show(self) -> None:
        self.show_calls += 1


def test_decrypt_visible_messages_does_not_hide_overlay_for_screenshot() -> None:
    overlay = VisibleOverlayProbe()
    window = SimpleNamespace(wrapper=SimpleNamespace(descendants=lambda: []))
    areas = DockAreas(Rect(0, 0, 800, 600), Rect(0, 0, 800, 400), Rect(0, 400, 800, 200))

    with patch.object(overlay_app.WINDOW_CACHE, "get", return_value=window), patch.object(overlay_app, "wechat_rect", return_value=areas), patch.object(overlay_app.ImageGrab, "grab", return_value=Image.new("RGB", (800, 400))):
        overlay_app.decrypt_visible_messages(lambda: "key", overlay)

    assert overlay.hide_calls == 0
    assert overlay.show_calls == 0


def test_decrypt_visible_messages_allows_overlay_foreground_for_side_screenshot() -> None:
    overlay = VisibleOverlayProbe()
    window = SimpleNamespace(wrapper=SimpleNamespace(descendants=lambda: []))
    areas = DockAreas(Rect(0, 0, 800, 600), Rect(0, 0, 800, 400), Rect(0, 400, 800, 200))

    def fake_wechat_rect(*, allow_overlay_foreground: bool = False):
        return areas if allow_overlay_foreground else None

    with patch.object(overlay_app.WINDOW_CACHE, "get", return_value=window), patch.object(overlay_app, "wechat_rect", side_effect=fake_wechat_rect), patch.object(overlay_app.ImageGrab, "grab", return_value=Image.new("RGB", (800, 400))) as grab:
        overlay_app.decrypt_visible_messages(lambda: "key", overlay)

    grab.assert_called_once()
