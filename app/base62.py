"""Base62 encoding for compact, URL-safe short codes.

A monotonically increasing integer id is encoded into a short string using the
62-character alphabet [0-9A-Za-z]. This is the classic approach used by URL
shorteners: it produces dense, collision-free codes (one code per id) that get
longer only as the id space grows:

    id 0          -> "0"
    id 61         -> "z"
    id 62         -> "10"
    id 916,132,832 -> "zzzzz"  (5 chars covers ~916M links)
"""

from __future__ import annotations

ALPHABET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
BASE = len(ALPHABET)
_INDEX = {char: i for i, char in enumerate(ALPHABET)}


def encode(number: int) -> str:
    """Encode a non-negative integer into a base62 string."""
    if number < 0:
        raise ValueError("number must be non-negative")
    if number == 0:
        return ALPHABET[0]
    chars: list[str] = []
    while number > 0:
        number, rem = divmod(number, BASE)
        chars.append(ALPHABET[rem])
    return "".join(reversed(chars))


def decode(code: str) -> int:
    """Decode a base62 string back into an integer."""
    if not code:
        raise ValueError("code must not be empty")
    number = 0
    for char in code:
        try:
            number = number * BASE + _INDEX[char]
        except KeyError as exc:
            raise ValueError(f"invalid base62 character: {char!r}") from exc
    return number
