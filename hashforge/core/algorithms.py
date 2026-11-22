"""Runtime algorithm registry, including optional OpenSSL algorithms."""

from collections.abc import Callable
from dataclasses import dataclass
import hashlib
from typing import Protocol
import zlib

from .crc import crc16_ccitt, crc16_modbus, crc32c, crc64_ecma


class Digest(Protocol):
    """Minimal incremental digest interface."""

    def update(self, data: bytes) -> None: ...
    def digest(self) -> bytes: ...
    def hexdigest(self) -> str: ...


class ZlibDigest:
    """Incremental zlib checksum adapter."""

    def __init__(self, adler: bool = False) -> None:
        self._function = zlib.adler32 if adler else zlib.crc32
        self._value = 1 if adler else 0

    def update(self, data: bytes) -> None:
        """Consume bytes."""
        self._value = self._function(data, self._value)

    def digest(self) -> bytes:
        """Return big-endian bytes."""
        return self._value.to_bytes(4, "big")

    def hexdigest(self) -> str:
        """Return fixed-width hexadecimal."""
        return self.digest().hex()


@dataclass(frozen=True)
class Algorithm:
    """Algorithm metadata and constructor."""

    id: str
    label: str
    factory: Callable[[], Digest]
    digest_size: int
    secure: bool = True
    checksum: bool = False


def registry() -> dict[str, Algorithm]:
    """Return algorithms usable in this Python/OpenSSL runtime."""
    result = {}
    names = (
        ("md5", "MD5"), ("sha1", "SHA-1"), ("sha224", "SHA-224"),
        ("sha256", "SHA-256"), ("sha384", "SHA-384"), ("sha512", "SHA-512"),
        ("sha512_256", "SHA-512/256"), ("sha3_224", "SHA3-224"),
        ("sha3_256", "SHA3-256"), ("sha3_384", "SHA3-384"),
        ("sha3_512", "SHA3-512"), ("blake2b", "BLAKE2b"),
        ("blake2s", "BLAKE2s"), ("ripemd160", "RIPEMD-160"),
    )
    for name, label in names:
        try:
            digest = hashlib.new(name)
        except ValueError:
            continue
        result[name] = Algorithm(
            name, label, lambda n=name: hashlib.new(n), digest.digest_size,
            name not in {"md5", "sha1", "ripemd160"},
        )
    for name, label, factory, size in (
        ("crc32", "CRC-32", ZlibDigest, 4),
        ("crc32c", "CRC-32C", crc32c, 4),
        ("crc16_ccitt", "CRC-16/CCITT-FALSE", crc16_ccitt, 2),
        ("crc16_modbus", "CRC-16/MODBUS", crc16_modbus, 2),
        ("crc64_ecma", "CRC-64/ECMA", crc64_ecma, 8),
        ("adler32", "Adler-32", lambda: ZlibDigest(True), 4),
    ):
        result[name] = Algorithm(name, label, factory, size, False, True)
    return result


def preset(name: str) -> tuple[str, ...]:
    """Return an algorithm selection preset."""
    if name == "All":
        return tuple(registry())
    if name == "Network/Forensics":
        return ("md5", "sha1", "sha256", "crc32", "crc32c", "adler32")
    return ("md5", "sha1", "sha256", "sha512", "crc32")
