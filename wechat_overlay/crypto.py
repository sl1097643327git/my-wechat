from __future__ import annotations

import os
import zlib

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

from wechat_overlay.radix_text import decode_radix_text, encode_radix_text

PREFIX = "密4:"
SALT_SIZE = 16
NONCE_SIZE = 12
KEY_SIZE = 32
PBKDF2_ITERATIONS = 210_000
ITERATION_CODE = 4
COMPRESSED_ITERATION_CODE = 5
COMPRESSION_MIN_SAVED_CHARS = 10


class CryptoError(ValueError):
    """Raised when encryption input is invalid."""


def is_encrypted(text: str) -> bool:
    normalized = text.strip()
    return normalized.startswith(PREFIX) and len(normalized) > len(PREFIX)


def encrypt_text(passphrase: str, plaintext: str, *, force_compression: bool | None = None) -> str:
    if not passphrase.strip():
        raise CryptoError("Passphrase is required.")

    salt = os.urandom(SALT_SIZE)
    nonce = os.urandom(NONCE_SIZE)
    key = _derive_key(passphrase, salt, PBKDF2_ITERATIONS)
    plaintext_bytes = plaintext.encode("utf-8")
    compressed_bytes = _compress_raw_deflate(plaintext_bytes)
    if force_compression is None:
        use_compression = _display_length_saved(plaintext_bytes, compressed_bytes) >= COMPRESSION_MIN_SAVED_CHARS
    else:
        use_compression = force_compression
    content = compressed_bytes if use_compression else plaintext_bytes
    iteration_code = COMPRESSED_ITERATION_CODE if use_compression else ITERATION_CODE
    ciphertext = AESGCM(key).encrypt(nonce, content, None)
    payload = bytes([iteration_code]) + salt + nonce + ciphertext
    return f"{PREFIX}{encode_radix_text(payload)}"


def decrypt_text(passphrase: str, encrypted_text: str) -> str | None:
    text = encrypted_text.strip()
    if not is_encrypted(text):
        return None

    try:
        payload_bytes = decode_radix_text(text[len(PREFIX) :])
        minimum_size = 1 + SALT_SIZE + NONCE_SIZE + 16
        if len(payload_bytes) < minimum_size or payload_bytes[0] not in {ITERATION_CODE, COMPRESSED_ITERATION_CODE}:
            return None
        is_compressed = payload_bytes[0] == COMPRESSED_ITERATION_CODE
        salt_start = 1
        nonce_start = salt_start + SALT_SIZE
        ciphertext_start = nonce_start + NONCE_SIZE
        salt = payload_bytes[salt_start:nonce_start]
        nonce = payload_bytes[nonce_start:ciphertext_start]
        ciphertext = payload_bytes[ciphertext_start:]
        key = _derive_key(passphrase, salt, PBKDF2_ITERATIONS)
        plaintext = AESGCM(key).decrypt(nonce, ciphertext, None)
        if is_compressed:
            plaintext = _decompress_raw_deflate(plaintext)
        return plaintext.decode("utf-8")
    except (ValueError, TypeError, KeyError, InvalidTag, zlib.error):
        return None


def _display_length_saved(plaintext_bytes: bytes, compressed_bytes: bytes) -> int:
    return _final_display_length(plaintext_bytes) - _final_display_length(compressed_bytes)


def _final_display_length(content: bytes) -> int:
    sample_payload = bytes([ITERATION_CODE]) + (b"\0" * SALT_SIZE) + (b"\0" * NONCE_SIZE) + content + (b"\0" * 16)
    return len(PREFIX) + len(encode_radix_text(sample_payload))


def _compress_raw_deflate(data: bytes) -> bytes:
    compressor = zlib.compressobj(level=6, wbits=-15)
    return compressor.compress(data) + compressor.flush()


def _decompress_raw_deflate(data: bytes) -> bytes:
    decompressor = zlib.decompressobj(wbits=-15)
    output = decompressor.decompress(data) + decompressor.flush()
    if decompressor.unused_data or not decompressor.eof:
        raise zlib.error("Incomplete raw deflate stream.")
    return output


def _derive_key(passphrase: str, salt: bytes, iterations: int) -> bytes:
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=KEY_SIZE,
        salt=salt,
        iterations=iterations,
    )
    return kdf.derive(passphrase.encode("utf-8"))
