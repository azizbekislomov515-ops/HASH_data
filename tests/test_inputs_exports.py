"""Input validation, output compatibility, and offline metadata."""

import base64
import csv
import io
import json
from pathlib import Path
import shutil
import subprocess

import pytest

from hashforge.core.export import save_results, serialize
from hashforge.core.filetypes import metadata, sniff
from hashforge.core.hasher import decode_input, decode_key, detect_algorithms, hash_bytes, hash_file, matches


def test_inputs() -> None:
    assert decode_input("a\r\nb\rc\n", newline="LF") == b"a\nb\nc\n"
    assert decode_input("a\r\nb\rc\n", newline="CRLF") == b"a\r\nb\r\nc\r\n"
    assert decode_input("a\r\nb", newline="keep") == b"a\r\nb"
    assert decode_input("ab", encoding="utf-16le") == b"a\x00b\x00"
    assert decode_input("00 ff 12", "hex") == b"\x00\xff\x12"
    assert decode_input("YWJj", "base64") == b"abc"
    assert decode_key("YWJj", "base64") == b"abc"
    for text, mode in (("0", "hex"), ("zz", "hex"), ("YWJj\n", "base64"), ("=", "base64")):
        with pytest.raises(ValueError):
            decode_input(text, mode)
    with pytest.raises(ValueError):
        decode_input("\u00e9", encoding="ascii")


def test_encodings_detection_and_matches() -> None:
    result = hash_bytes(b"abc", ["sha256"])[0]
    assert base64.b64decode(result.formatted("base64")) == result.value
    assert result.formatted(uppercase=True) == result.value.hex().upper()
    assert result.formatted("decimal") == ""
    assert {"sha256", "sha3_256", "blake2s"} <= set(detect_algorithms(result.formatted()))
    assert matches(result, result.formatted(uppercase=True))
    assert not matches(result, "00" * 32)
    assert detect_algorithms("xyz") == ()
    assert hash_bytes(b"123456789", ["crc32"])[0].formatted("decimal") == "3421780262"


def test_exports(tmp_path: Path) -> None:
    path = tmp_path / "data with spaces.bin"
    path.write_bytes(b"abc")
    results = hash_file(path, ["sha256"])
    assert json.loads(serialize(results))[0]["hash"] == results[0].formatted()
    assert list(csv.DictReader(io.StringIO(serialize(results, "csv"))))[0]["file"] == str(path)
    manifest = tmp_path / "checksums.sha256"
    save_results(manifest, results, "sum")
    assert manifest.read_text() == f"{results[0].formatted()}  data with spaces.bin\n"
    if shutil.which("sha256sum"):
        process = subprocess.run(["sha256sum", "-c", str(manifest)], cwd=tmp_path, capture_output=True)
        assert process.returncode == 0, process.stderr
    with pytest.raises(ValueError):
        serialize(hash_file(path, ["md5", "sha256"]), "sum")
    with pytest.raises(ValueError):
        serialize(hash_file(path, ["sha256"], b"key"), "sum")


@pytest.mark.parametrize("signature,mime", [
    (b"\x89PNG\r\n\x1a\n", "image/png"), (b"\xff\xd8\xff", "image/jpeg"),
    (b"GIF89a", "image/gif"), (b"%PDF-1.7", "application/pdf"),
    (b"PK\x03\x04", "application/zip"), (b"\x7fELF", "application/x-elf"),
    (b"MZ", "application/vnd.microsoft.portable-executable"),
    (b"\xd4\xc3\xb2\xa1", "application/vnd.tcpdump.pcap"),
    (b"\x0a\x0d\x0d\x0a", "application/x-pcapng"),
])
def test_magic(signature: bytes, mime: str, tmp_path: Path) -> None:
    assert sniff(signature, "wrong.txt") == mime
    path = tmp_path / "wrong.txt"
    path.write_bytes(signature)
    assert metadata(path)["mime"] == mime
