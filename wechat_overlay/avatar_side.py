from __future__ import annotations

from dataclasses import dataclass

from PIL import Image

from wechat_overlay.dock_layout import Rect


@dataclass(frozen=True)
class SideScore:
    left_pixels: int
    right_pixels: int

    @property
    def side(self) -> str | None:
        total = self.left_pixels + self.right_pixels
        margin = abs(self.right_pixels - self.left_pixels)
        if total < 80 or margin < 120:
            return None
        return "right" if self.right_pixels > self.left_pixels else "left"


def score_message_side(image: Image.Image, chat: Rect, row: Rect, *, edge_width: int = 96) -> SideScore:
    image = image.convert("RGB")
    width, height = image.size
    left = max(0, chat.x)
    right = min(width, chat.x + chat.width)
    top = max(0, row.y, chat.y)
    bottom = min(height, row.y + row.height, chat.y + chat.height)
    left_strip_right = min(right, left + edge_width)
    right_strip_left = max(left, right - edge_width)

    left_pixels = 0
    right_pixels = 0
    for y in range(top, bottom):
        for x in range(left, left_strip_right):
            r, g, b = image.getpixel((x, y))
            if _is_sender_signal_pixel(r, g, b):
                left_pixels += 1
        for x in range(right_strip_left, right):
            r, g, b = image.getpixel((x, y))
            if _is_sender_signal_pixel(r, g, b):
                right_pixels += 1
    return SideScore(left_pixels, right_pixels)


def _is_sender_signal_pixel(r: int, g: int, b: int) -> bool:
    is_background = r > 230 and g > 230 and b > 230
    is_overlay_yellow = r > 220 and g > 170 and b < 130
    return not is_background and not is_overlay_yellow
