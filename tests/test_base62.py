import pytest

from app import base62


def test_encode_known_values():
    assert base62.encode(0) == "0"
    assert base62.encode(61) == "z"
    assert base62.encode(62) == "10"


def test_encode_decode_roundtrip():
    for n in [0, 1, 61, 62, 1000, 100_000, 916_132_831, 10**12]:
        assert base62.decode(base62.encode(n)) == n


def test_encode_is_monotonic_in_length():
    assert len(base62.encode(61)) == 1
    assert len(base62.encode(62)) == 2
    assert len(base62.encode(62 * 62 - 1)) == 2
    assert len(base62.encode(62 * 62)) == 3


def test_negative_raises():
    with pytest.raises(ValueError):
        base62.encode(-1)


def test_decode_invalid_char_raises():
    with pytest.raises(ValueError):
        base62.decode("abc!")
    with pytest.raises(ValueError):
        base62.decode("")
