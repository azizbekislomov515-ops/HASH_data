"""RFC 2202 and RFC 4231 HMAC vectors."""

import hmac
import pytest
from hashforge.core.algorithms import registry
from hashforge.core.hasher import decode_key, hash_bytes


@pytest.mark.parametrize("name,length,expected", [
    ("md5", 16, "9294727a3638bb1c13f48ef8158bfc9d"),
    ("sha1", 20, "b617318655057264e28bc0b6fb378c8ef146be00"),
    ("sha256", 20, "b0344c61d8db38535ca8afceaf0bf12b881dc200c9833da726e9376c2e32cff7"),
    ("sha512", 20, "87aa7cdea5ef619d4ff0b4241a1d6cb02379f4e2ce4ec2787ad0b30545e17cde" "daa833b7d6b8a702038b274eaea3f4e4be9d914eeb61f1702e696c203a126854"),
])
def test_rfc(name: str, length: int, expected: str) -> None:
    assert hash_bytes(b"Hi There", [name], b"\x0b" * length)[0].formatted() == expected


@pytest.mark.parametrize("name", [n for n, a in registry().items() if not a.checksum])
def test_all_hmac(name: str) -> None:
    assert hash_bytes(b"abc", [name], b"secret")[0].value == hmac.digest(b"secret", b"abc", name)


@pytest.mark.parametrize("value,mode", [("", "text"), ("xx", "hex"), ("abc", "base64")])
def test_invalid_key(value: str, mode: str) -> None:
    with pytest.raises(ValueError):
        decode_key(value, mode)
