import pytest

from wechat_overlay.crypto import COMPRESSION_MIN_SAVED_CHARS, PREFIX, CryptoError, decrypt_text, encrypt_text, is_encrypted
from wechat_overlay.radix_text import decode_radix_text


def test_encrypt_then_decrypt_round_trips_chinese_text():
    cipher = encrypt_text("shared-key", "你好，文件传输助手")

    assert cipher.startswith("密4:")
    assert decrypt_text("shared-key", cipher) == "你好，文件传输助手"


def test_encrypt_uses_compact_binary_payload_without_legacy_json_prefix():
    cipher = encrypt_text("shared-key", "短消息")

    assert cipher.startswith("密4:")
    assert len(cipher) < 60
    assert not cipher.startswith("ENC[v1]:")
    assert not cipher.startswith("E2:")


def test_wrong_key_returns_none():
    cipher = encrypt_text("shared-key", "hidden")

    assert decrypt_text("wrong-key", cipher) is None


def test_wrong_key_on_compressed_payload_returns_none():
    cipher = encrypt_text("shared-key", "重复内容" * 120)

    assert decrypt_text("wrong-key", cipher) is None


def test_malformed_payload_returns_none():
    assert decrypt_text("shared-key", "密4:not-valid") is None


def test_corrupt_compressed_payload_returns_none():
    cipher = encrypt_text("shared-key", "重复内容" * 120)
    payload = bytearray(decode_radix_text(cipher[len(PREFIX) :]))
    payload[-1] ^= 0xFF

    from wechat_overlay.radix_text import encode_radix_text

    assert decrypt_text("shared-key", f"{PREFIX}{encode_radix_text(bytes(payload))}") is None


def test_is_encrypted_checks_versioned_prefix():
    assert is_encrypted("密4:abc")
    assert not is_encrypted("密3:abc")
    assert not is_encrypted("E2:abc")
    assert not is_encrypted("ENC[v1]:abc")
    assert not is_encrypted("hello")


def test_encrypt_text_does_not_add_outgoing_marker():
    cipher = encrypt_text("shared-key", "自己发的消息")

    assert not cipher.startswith("ME:")
    assert decrypt_text("shared-key", cipher) == "自己发的消息"


def test_encrypt_skips_compression_when_display_savings_is_less_than_10_chars():
    cipher = encrypt_text("shared-key", "短消息")
    payload = decode_radix_text(cipher[len(PREFIX) :])

    assert payload[0] == 4


def test_encrypt_uses_compression_when_display_savings_reaches_threshold():
    text = "重复内容" * 120
    cipher = encrypt_text("shared-key", text)
    payload = decode_radix_text(cipher[len(PREFIX) :])

    assert payload[0] == 5
    assert decrypt_text("shared-key", cipher) == text


def test_compression_saves_at_least_configured_display_characters():
    text = "重复内容" * 120
    compressed_cipher = encrypt_text("shared-key", text)
    uncompressed_cipher = encrypt_text("shared-key", text, force_compression=False)

    assert len(uncompressed_cipher) - len(compressed_cipher) >= COMPRESSION_MIN_SAVED_CHARS


def test_varied_texts_round_trip_stably() -> None:
    texts = ["", "好", "emoji🙂测试", "换行\n第二行", "a" * 512, "重复内容" * 300]

    for text in texts:
        assert decrypt_text("shared-key", encrypt_text("shared-key", text)) == text


def test_encrypt_rejects_empty_key():
    with pytest.raises(CryptoError):
        encrypt_text("", "hello")
