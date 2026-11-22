"""CLI verification and safe key-input extensions."""

import io
import json
import pytest

from hashforge.cli import main


def test_environment_key_and_verification(monkeypatch: pytest.MonkeyPatch) -> None:
    """Environment keys and constant-time verification share the core."""
    monkeypatch.setenv("HASHFORGE_TEST_KEY", "0b" * 16)
    output, error = io.StringIO(), io.StringIO()
    args = ["--text", "Hi There", "--algo", "md5", "--hmac-key-env",
            "HASHFORGE_TEST_KEY", "--key-mode", "hex", "--format", "json",
            "--verify", "9294727a3638bb1c13f48ef8158bfc9d"]
    assert main(args, output, error) == 0
    assert json.loads(output.getvalue())[0]["algorithm"] == "hmac-md5"
    assert error.getvalue() == "MATCH\n"
    assert main(["--text", "abc", "--verify", "00" * 32], output, error) == 1


def test_list_and_empty_input() -> None:
    """List runtime algorithm IDs and accept intentionally empty text."""
    output = io.StringIO()
    assert main(["--list-algorithms"], output) == 0
    assert "sha256" in output.getvalue()
    assert main(["--text", "", "--algo", "sha256"], output) == 0
