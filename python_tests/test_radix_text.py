import os

import pytest

from wechat_overlay.radix_text import RADIX_ALPHABET, decode_radix_text, encode_radix_text


def test_radix_alphabet_is_expanded_for_shorter_display_text() -> None:
    assert len(RADIX_ALPHABET) >= 4096


@pytest.mark.parametrize("data", [b"", b"\x00", b"\x00\x00\x01", b"hello", bytes(range(256))])
def test_radix_text_round_trips_edge_cases(data: bytes) -> None:
    assert decode_radix_text(encode_radix_text(data)) == data


def test_radix_text_round_trips_random_payloads() -> None:
    for size in range(0, 257):
        data = os.urandom(size)

        assert decode_radix_text(encode_radix_text(data)) == data


def test_radix_text_rejects_invalid_characters() -> None:
    with pytest.raises(ValueError):
        decode_radix_text("🙂")
