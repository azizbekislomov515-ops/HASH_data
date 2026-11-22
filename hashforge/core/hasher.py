"""Streaming hash computation, input parsing, and constant-time verification."""

import base64
import binascii
from collections.abc import Callable, Iterable
from dataclasses import dataclass
import hmac
import os
from pathlib import Path
import time

from .algorithms import Digest, registry


class Cancelled(Exception):
    """Raised when a computation is cancelled."""


@dataclass(frozen=True)
class Result:
    """One digest, with source and algorithm metadata."""

    source: str
    size: int
    algorithm: str
    value: bytes
    is_hmac: bool = False
    checksum: bool = False

    @property
    def label(self) -> str:
        """Return the unambiguous algorithm identifier."""
        return f"hmac-{self.algorithm}" if self.is_hmac else self.algorithm

    def formatted(self, encoding: str = "hex", uppercase: bool = False) -> str:
        """Encode digest bytes for display or export."""
        if encoding == "base64":
            return base64.b64encode(self.value).decode("ascii")
        if encoding == "decimal":
            if not self.checksum:
                return ""
            return str(int.from_bytes(self.value, "big"))
        value = self.value.hex()
        return value.upper() if uppercase else value


def decode_input(text: str, mode: str = "text", encoding: str = "utf-8",
                 newline: str = "keep") -> bytes:
    """Decode strict hex/Base64 or encode text with newline normalization."""
    if mode == "hex":
        try:
            return bytes.fromhex(text)
        except ValueError as exc:
            raise ValueError("Invalid hex: enter complete pairs of hexadecimal digits.") from exc
    if mode == "base64":
        try:
            return base64.b64decode(text.encode("ascii"), validate=True)
        except (ValueError, UnicodeError, binascii.Error) as exc:
            raise ValueError("Invalid Base64: check characters and padding (no whitespace).") from exc
    if newline != "keep":
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        if newline == "CRLF":
            text = text.replace("\n", "\r\n")
    try:
        return text.encode(encoding)
    except UnicodeError as exc:
        raise ValueError(f"Text cannot be represented as {encoding}.") from exc


def decode_key(text: str, mode: str = "text") -> bytes:
    """Decode a nonempty HMAC key without persisting it."""
    key = decode_input(text, mode)
    if not key:
        raise ValueError("The HMAC secret key must not be empty.")
    return key


def _hashers(algorithms: Iterable[str], key: bytes | None) -> dict[str, Digest]:
    available = registry()
    result: dict[str, Digest] = {}
    if key == b"":
        raise ValueError("The HMAC secret key must not be empty.")
    for name in algorithms:
        if name not in available:
            raise ValueError(f"Unknown or unavailable algorithm: {name}")
        algorithm = available[name]
        if key is not None and not algorithm.checksum:
            result[name] = hmac.new(key, digestmod=algorithm.factory)
        else:
            result[name] = algorithm.factory()
    if not result:
        raise ValueError("Select at least one algorithm.")
    return result


def hash_chunks(chunks: Iterable[bytes], algorithms: Iterable[str],
                source: str = "Text", key: bytes | None = None,
                cancelled: Callable[[], bool] = lambda: False,
                progress: Callable[[int, float], None] | None = None) -> list[Result]:
    """Update all requested algorithms in one pass over an iterable of chunks."""
    hashers = _hashers(algorithms, key)
    size = 0
    start = time.monotonic()
    for chunk in chunks:
        if cancelled():
            raise Cancelled()
        for hasher in hashers.values():
            hasher.update(chunk)
        size += len(chunk)
        if progress:
            progress(size, time.monotonic() - start)
    if cancelled():
        raise Cancelled()
    available = registry()
    return [Result(source, size, name, hasher.digest(),
                   key is not None and not available[name].checksum,
                   available[name].checksum) for name, hasher in hashers.items()]


def hash_bytes(data: bytes, algorithms: Iterable[str], key: bytes | None = None,
               cancelled: Callable[[], bool] = lambda: False) -> list[Result]:
    """Hash in-memory input in cancellation-friendly chunks."""
    chunks = (data[i:i + 65536] for i in range(0, len(data), 65536))
    return hash_chunks(chunks, algorithms, key=key, cancelled=cancelled)


def hash_file(path: str | Path, algorithms: Iterable[str], key: bytes | None = None,
              chunk_size: int = 4 * 1024 * 1024,
              cancelled: Callable[[], bool] = lambda: False,
              progress: Callable[[int, float], None] | None = None) -> list[Result]:
    """Stream any file as raw bytes; reject files changed or removed during reading."""
    if chunk_size < 1:
        raise ValueError("Chunk size must be positive.")
    path = Path(path).resolve()
    with path.open("rb") as stream:
        before = os.fstat(stream.fileno())
        results = hash_chunks(iter(lambda: stream.read(chunk_size), b""), algorithms,
                              str(path), key, cancelled, progress)
        after = os.fstat(stream.fileno())
        current = path.stat()
    signature = lambda stat: (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns)
    if signature(before) != signature(after) or signature(before) != signature(current):
        raise OSError("File changed during hashing; calculate it again.")
    return results


def detect_algorithms(expected: str) -> tuple[str, ...]:
    """Return all possible algorithms for a hex digest; length is ambiguous."""
    try:
        value = bytes.fromhex(expected.strip())
    except ValueError:
        return ()
    return tuple(name for name, item in registry().items() if item.digest_size == len(value))


def matches(result: Result, expected: str) -> bool:
    """Compare a hex expectation in constant time."""
    try:
        value = bytes.fromhex(expected.strip())
    except ValueError as exc:
        raise ValueError("Expected hash must be hexadecimal.") from exc
    return hmac.compare_digest(result.value, value)
