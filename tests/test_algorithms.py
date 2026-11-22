"""Known-answer vectors and streaming reference checks."""

import hashlib
import json
from pathlib import Path
import pytest
from hashforge.core.algorithms import registry
from hashforge.core.hasher import hash_bytes


@pytest.mark.parametrize("name,expected", [
    ("md5", "900150983cd24fb0d6963f7d28e17f72"),
    ("sha1", "a9993e364706816aba3e25717850c26c9cd0d89d"),
    ("sha224", "23097d223405d8228642a477bda255b32aadbce4bda0b3f7e36c9da7"),
    ("sha256", "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"),
    ("sha384", "cb00753f45a35e8bb5a03d699ac65007272c32ab0eded1631a8b605a43ff5bed8086072ba1e7cc2358baeca134c825a7"),
    ("sha512", "ddaf35a193617abacc417349ae20413112e6fa4e89a97ea20a9eeee64b55d39a2192992a274fc1a836ba3c23a3feebbd454d4423643ce80e2a9ac94fa54ca49f"),
    ("sha512_256", "53048e2681941ef99b2e29b76b4c7dabe4c2d0c634fc6d46e0e2f13107e7af23"),
    ("sha3_224", "e642824c3f8cf24ad09234ee7d3c766fc9a3a5168d0c94ad73b46fdf"),
    ("sha3_256", "3a985da74fe225b2045c172d6bd390bd855f086e3e9d525b46bfe24511431532"),
    ("sha3_384", "ec01498288516fc926459f58e2c6ad8df9b473cb0fc08c2596da7cf0e49be4b298d88cea927ac7f539f1edf228376d25"),
    ("sha3_512", "b751850b1a57168a5693cd924b6b096e08f621827444f70d884f5d0240d2712e10e116e9192af3c91a7ec57647e3934057340b4cf408d5a56592f8274eec53f0"),
    ("blake2b", "ba80a53f981c4d0d6a2797b69f12f6e94c212f14685ac4b74b12bb6fdbffa2d17d87c5392aab792dc252d5de4533cc9518d38aa8dbf1925ab92386edd4009923"),
    ("blake2s", "508c5e8c327c14e2e1a72ba34eeb452f37458b209ed63a294d999b4c86675982"),
    ("ripemd160", "8eb208f7e05d987a9b044a8e98c6b087f15a0bfc"),
    ("crc32", "352441c2"), ("adler32", "024d0127"),
])
def test_abc(name: str, expected: str) -> None:
    if name not in registry():
        pytest.skip("Not available in OpenSSL")
    assert hash_bytes(b"abc", [name])[0].formatted() == expected


@pytest.mark.parametrize("name", [n for n, a in registry().items() if not a.checksum])
@pytest.mark.parametrize("data", [b"", b"a" * 1_000_000])
def test_empty_and_long_against_reference(name: str, data: bytes) -> None:
    assert hash_bytes(data, [name])[0].value == hashlib.new(name, data).digest()
    vectors = json.loads(Path(__file__).with_name("vectors.json").read_text())
    assert hash_bytes(data, [name])[0].formatted() == vectors[name][bool(data)]
