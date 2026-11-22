"""Offline command-line access to the shared hashing core."""

import argparse
from collections.abc import Sequence
import os
from pathlib import Path
import sys
from typing import TextIO

from .core.algorithms import registry
from .core.export import save_results, serialize
from .core.hasher import decode_input, decode_key, hash_bytes, hash_file, matches


def main(argv: Sequence[str] | None = None, stdout: TextIO | None = None,
         stderr: TextIO | None = None) -> int:
    """Calculate hashes and return a process exit code."""
    parser = argparse.ArgumentParser(prog="HashForge")
    stdout = stdout if stdout is not None else sys.stdout
    stderr = stderr if stderr is not None else sys.stderr
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--file", type=Path, help="Hash any file as raw bytes")
    source.add_argument("--text", help="Hash literal text")
    parser.add_argument("--algo", default="sha256", help="Comma-separated algorithm IDs")
    keys = parser.add_mutually_exclusive_group()
    keys.add_argument("--hmac-key", help="Secret key; omit for ordinary hashes")
    keys.add_argument("--hmac-key-env", help="Read the secret from this environment variable")
    parser.add_argument("--list-algorithms", action="store_true")
    parser.add_argument("--verify", help="Expected hex digest; requires one algorithm")
    parser.add_argument("--key-mode", choices=("text", "hex", "base64"), default="text")
    parser.add_argument("--input-mode", choices=("text", "hex", "base64"), default="text")
    parser.add_argument("--encoding", choices=("utf-8", "utf-16le", "ascii", "latin-1"), default="utf-8")
    parser.add_argument("--newline", choices=("keep", "LF", "CRLF"), default="keep")
    parser.add_argument("--format", choices=("txt", "csv", "json", "sum"), default="txt")
    parser.add_argument("--output", type=Path, help="Write results to this file")
    args = parser.parse_args(argv)
    try:
        if args.list_algorithms:
            if stdout is not None:
                stdout.write("\n".join(f"{a.id:16} {a.label}" for a in registry().values()) + "\n")
            return 0
        if args.file is None and args.text is None:
            raise ValueError("Specify --file or --text.")
        key_text = args.hmac_key
        if args.hmac_key_env is not None:
            if args.hmac_key_env not in os.environ:
                raise ValueError(f"Environment variable is not set: {args.hmac_key_env}")
            key_text = os.environ[args.hmac_key_env]
        key = decode_key(key_text, args.key_mode) if key_text is not None else None
        algorithms = tuple(registry()) if args.algo == "all" else tuple(dict.fromkeys(
            name.strip().lower() for name in args.algo.split(",")
        ))
        if args.verify is not None and len(algorithms) != 1:
            raise ValueError("Verification requires exactly one algorithm.")
        if args.file:
            results = hash_file(args.file, algorithms, key)
        else:
            data = decode_input(args.text, args.input_mode, args.encoding, args.newline)
            results = hash_bytes(data, algorithms, key)
        if args.output:
            save_results(args.output, results, args.format)
        elif stdout is not None:
            stdout.write(serialize(results, args.format))
        else:
            raise ValueError("This windowed executable requires --output for CLI results.")
        if args.verify is not None:
            matched = matches(results[0], args.verify)
            if stderr is not None:
                stderr.write("MATCH\n" if matched else "MISMATCH\n")
            return 0 if matched else 1
        return 0
    except (OSError, ValueError) as exc:
        if stderr is not None:
            print(f"HashForge: {exc}", file=stderr)
        return 1
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
