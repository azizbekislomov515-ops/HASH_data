"""Offline file metadata and conservative signature sniffing."""

from datetime import datetime
import mimetypes
from pathlib import Path


def sniff(data: bytes, filename: str = "") -> str:
    """Identify common magic signatures, falling back to the filename."""
    signatures = (
        (b"\x89PNG\r\n\x1a\n", "image/png"), (b"\xff\xd8\xff", "image/jpeg"),
        (b"GIF87a", "image/gif"), (b"GIF89a", "image/gif"),
        (b"%PDF-", "application/pdf"), (b"PK\x03\x04", "application/zip"),
        (b"PK\x05\x06", "application/zip"), (b"\x7fELF", "application/x-elf"),
        (b"MZ", "application/vnd.microsoft.portable-executable"),
        (b"\xd4\xc3\xb2\xa1", "application/vnd.tcpdump.pcap"),
        (b"\xa1\xb2\xc3\xd4", "application/vnd.tcpdump.pcap"),
        (b"\x4d\x3c\xb2\xa1", "application/vnd.tcpdump.pcap"),
        (b"\xa1\xb2\x3c\x4d", "application/vnd.tcpdump.pcap"),
        (b"\x0a\x0d\x0d\x0a", "application/x-pcapng"),
    )
    for signature, mime in signatures:
        if data.startswith(signature):
            return mime
    return mimetypes.guess_type(filename)[0] or "application/octet-stream"


def metadata(path: str | Path) -> dict[str, str | int]:
    """Read stat data and a small signature prefix."""
    path = Path(path).resolve()
    stat = path.stat()
    with path.open("rb") as stream:
        mime = sniff(stream.read(512), path.name)
    return {"name": path.name, "path": str(path), "size": stat.st_size,
            "mime": mime, "modified": datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat()}
