"""Single-pass streaming, mutation detection, and cancellation."""

import pytest
from pathlib import Path
from hashforge.core.algorithms import registry
from hashforge.core.hasher import Cancelled, hash_bytes, hash_file


def test_stream(tmp_path: Path) -> None:
    data = bytes(range(256)) * 1000
    path = tmp_path / "arbitrary.pcap"
    path.write_bytes(data)
    expected = hash_bytes(data, registry())
    actual = hash_file(path, registry(), chunk_size=777)
    assert [r.value for r in actual] == [r.value for r in expected]


def test_cancel(tmp_path: Path) -> None:
    path = tmp_path / "data"
    path.write_bytes(b"abc")
    with pytest.raises(Cancelled):
        hash_file(path, ["sha256"], cancelled=lambda: True)


def test_changed(tmp_path: Path) -> None:
    path = tmp_path / "data"
    path.write_bytes(b"abc")
    def progress(size: int, elapsed: float) -> None:
        path.write_bytes(b"different")
    with pytest.raises(OSError):
        hash_file(path, ["sha256"], progress=progress)
