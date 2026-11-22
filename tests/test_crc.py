"""Published CRC check values and incremental behavior."""

import pytest
from collections.abc import Callable
from hashforge.core.crc import CRC
from hashforge.core.hasher import hash_bytes
from hashforge.core.crc import crc16_ccitt, crc16_modbus, crc32c, crc64_ecma


@pytest.mark.parametrize("factory,check,empty", [
    (crc16_ccitt, "29b1", "ffff"), (crc16_modbus, "4b37", "ffff"),
    (crc32c, "e3069283", "00000000"),
    (crc64_ecma, "6c40df5f0b497347", "0000000000000000"),
])
def test_crc_vectors(factory: Callable[[], CRC], check: str, empty: str) -> None:
    digest = factory()
    assert digest.hexdigest() == empty
    digest.update(b"1234")
    clone = digest.copy()
    digest.update(b"56789")
    clone.update(b"56789")
    assert digest.hexdigest() == clone.hexdigest() == check


@pytest.mark.parametrize("factory,width,poly,initial,reflected,xor_out", [
    (crc16_ccitt, 16, 0x1021, 0xFFFF, False, 0),
    (crc16_modbus, 16, 0xA001, 0xFFFF, True, 0),
    (crc32c, 32, 0x82F63B78, 0xFFFFFFFF, True, 0xFFFFFFFF),
    (crc64_ecma, 64, 0x42F0E1EBA9EA3693, 0, False, 0),
])
@pytest.mark.parametrize("data", [b"", b"abc", bytes(range(256)) * 128])
def test_against_bitwise_reference(
    factory: Callable[[], CRC], width: int, poly: int, initial: int,
    reflected: bool, xor_out: int, data: bytes,
) -> None:
    """Cross-check tables with a separate, slow bit-at-a-time implementation."""
    value = initial
    mask = (1 << width) - 1
    for byte in data:
        value ^= byte if reflected else byte << (width - 8)
        for _ in range(8):
            if reflected:
                value = (value >> 1) ^ (poly if value & 1 else 0)
            else:
                value = ((value << 1) ^ (poly if value & (1 << (width - 1)) else 0)) & mask
    digest = factory()
    for offset in range(0, len(data), 123):
        digest.update(data[offset:offset + 123])
    assert digest.digest() == (value ^ xor_out).to_bytes(width // 8, "big")


@pytest.mark.parametrize("algorithm,empty,check", [
    ("crc32", "00000000", "cbf43926"),
    ("adler32", "00000001", "091e01de"),
])
def test_zlib_vectors(algorithm: str, empty: str, check: str) -> None:
    assert hash_bytes(b"", [algorithm])[0].formatted() == empty
    assert hash_bytes(b"123456789", [algorithm])[0].formatted() == check
