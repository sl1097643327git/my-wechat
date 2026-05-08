from PIL import Image, ImageDraw

from wechat_overlay.avatar_side import score_message_side
from wechat_overlay.dock_layout import Rect


def test_score_message_side_detects_right_avatar_cluster() -> None:
    image = Image.new("RGB", (400, 200), (245, 245, 245))
    draw = ImageDraw.Draw(image)
    draw.rectangle((330, 60, 370, 100), fill=(80, 80, 80))

    score = score_message_side(image, Rect(0, 0, 400, 200), Rect(0, 40, 400, 100))

    assert score.side == "right"


def test_score_message_side_detects_left_avatar_cluster() -> None:
    image = Image.new("RGB", (400, 200), (245, 245, 245))
    draw = ImageDraw.Draw(image)
    draw.rectangle((30, 60, 70, 100), fill=(80, 80, 80))

    score = score_message_side(image, Rect(0, 0, 400, 200), Rect(0, 40, 400, 100))

    assert score.side == "left"


def test_score_message_side_ignores_message_body_outside_avatar_strips() -> None:
    image = Image.new("RGB", (400, 200), (245, 245, 245))
    draw = ImageDraw.Draw(image)
    draw.rectangle((30, 60, 70, 100), fill=(80, 80, 80))
    draw.rectangle((230, 60, 320, 100), fill=(80, 80, 80))

    score = score_message_side(image, Rect(0, 0, 400, 200), Rect(0, 40, 400, 100), edge_width=90)

    assert score.side == "left"


def test_score_message_side_is_unknown_when_avatar_evidence_is_weak() -> None:
    image = Image.new("RGB", (400, 200), (245, 245, 245))
    draw = ImageDraw.Draw(image)
    draw.rectangle((30, 60, 34, 64), fill=(80, 80, 80))

    score = score_message_side(image, Rect(0, 0, 400, 200), Rect(0, 40, 400, 100))

    assert score.side is None


def test_score_message_side_requires_meaningful_left_right_difference() -> None:
    image = Image.new("RGB", (400, 200), (245, 245, 245))
    draw = ImageDraw.Draw(image)
    draw.rectangle((30, 60, 70, 100), fill=(80, 80, 80))
    draw.rectangle((330, 60, 368, 100), fill=(80, 80, 80))

    score = score_message_side(image, Rect(0, 0, 400, 200), Rect(0, 40, 400, 100))

    assert score.side is None
