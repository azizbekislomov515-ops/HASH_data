"""CLI input validation and portable exports."""

import json
from pathlib import Path

from hashforge.cli import main


def test_json_file(tmp_path: Path) -> None:
    """The CLI shares raw-byte hashing and JSON output with the GUI."""
    source = tmp_path / "input.bin"
    target = tmp_path / "results.json"
    source.write_bytes(b"abc")
    assert main(["--file", str(source), "--algo", "sha256,md5",
                 "--format", "json", "--output", str(target)]) == 0
    rows = json.loads(target.read_text())
    assert len(rows) == 2
    assert rows[0]["hash"] == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"


def test_key_and_invalid_algorithm(tmp_path: Path) -> None:
    """Malformed keys and unavailable algorithms return failures."""
    assert main(["--text", "abc", "--hmac-key", ""]) == 1
    assert main(["--text", "abc", "--algo", "unknown"]) == 1
    target = tmp_path / "hmac.json"
    assert main(["--text", "Hi There", "--algo", "sha256", "--hmac-key", "0b" * 20,
                 "--key-mode", "hex", "--format", "json", "--output", str(target)]) == 0
    assert json.loads(target.read_text())[0]["algorithm"] == "hmac-sha256"
