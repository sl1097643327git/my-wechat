from __future__ import annotations


RADIX_ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ" + "".join(chr(codepoint) for codepoint in range(0x4E00, 0x9FA6))

_RADIX = len(RADIX_ALPHABET)
_CHAR_TO_VALUE = {char: index for index, char in enumerate(RADIX_ALPHABET)}
_LENGTH_BYTES = 2
_SENTINEL = 1


def encode_radix_text(data: bytes) -> str:
    if len(data) > 65535:
        raise ValueError("Payload is too large.")
    framed = bytes([_SENTINEL]) + len(data).to_bytes(_LENGTH_BYTES, "big") + data
    value = int.from_bytes(framed, "big")
    if value == 0:
        return RADIX_ALPHABET[0]
    chars: list[str] = []
    while value:
        value, digit = divmod(value, _RADIX)
        chars.append(RADIX_ALPHABET[digit])
    return "".join(reversed(chars))


def decode_radix_text(text: str) -> bytes:
    if not text:
        raise ValueError("Encoded payload is empty.")
    value = 0
    for char in text:
        try:
            digit = _CHAR_TO_VALUE[char]
        except KeyError as error:
            raise ValueError("Encoded payload contains an invalid character.") from error
        value = value * _RADIX + digit
    byte_count = max(1 + _LENGTH_BYTES, (value.bit_length() + 7) // 8)
    framed = value.to_bytes(byte_count, "big")
    if len(framed) < 1 + _LENGTH_BYTES or framed[0] != _SENTINEL:
        raise ValueError("Encoded payload is too short.")
    length = int.from_bytes(framed[1 : 1 + _LENGTH_BYTES], "big")
    data = framed[1 + _LENGTH_BYTES :]
    if len(data) != length:
        raise ValueError("Encoded payload length does not match.")
    return data
