"""Table-driven CRCs. Check values use the ASCII message '123456789'."""

from typing import Self


class CRC:
    """Incremental CRC with a hashlib-compatible interface."""

    block_size = 1

    def __init__(self, width: int, polynomial: int, initial: int,
                 reflected: bool, xor_out: int, name: str) -> None:
        self.width = width
        self.digest_size = width // 8
        self.name = name
        self._mask = (1 << width) - 1
        self._reflected = reflected
        self._xor_out = xor_out
        self._value = initial
        table = []
        for byte in range(256):
            value = byte if reflected else byte << (width - 8)
            for _ in range(8):
                if reflected:
                    value = (value >> 1) ^ (polynomial if value & 1 else 0)
                else:
                    value = ((value << 1) ^ (
                        polynomial if value & (1 << (width - 1)) else 0
                    )) & self._mask
            table.append(value)
        self._table = tuple(table)

    def update(self, data: bytes) -> None:
        """Consume another byte sequence."""
        value = self._value
        table = self._table
        if self._reflected:
            for byte in data:
                value = (value >> 8) ^ table[(value ^ byte) & 255]
        else:
            shift = self.width - 8
            mask = self._mask
            for byte in data:
                value = ((value << 8) & mask) ^ table[((value >> shift) ^ byte) & 255]
        self._value = value

    def digest(self) -> bytes:
        """Return the canonical big-endian checksum bytes."""
        return (self._value ^ self._xor_out).to_bytes(self.digest_size, "big")

    def hexdigest(self) -> str:
        """Return a fixed-width lowercase hexadecimal checksum."""
        return self.digest().hex()

    def copy(self) -> Self:
        """Clone the current checksum state."""
        import copy
        return copy.copy(self)


def crc32c() -> CRC:
    """Create CRC-32C (Castagnoli), check E3069283."""
    return CRC(32, 0x82F63B78, 0xFFFFFFFF, True, 0xFFFFFFFF, "crc32c")


def crc16_ccitt() -> CRC:
    """Create CRC-16/CCITT-FALSE, check 29B1."""
    return CRC(16, 0x1021, 0xFFFF, False, 0, "crc16_ccitt")


def crc16_modbus() -> CRC:
    """Create CRC-16/MODBUS, check 4B37."""
    return CRC(16, 0xA001, 0xFFFF, True, 0, "crc16_modbus")


def crc64_ecma() -> CRC:
    """Create CRC-64/ECMA-182, check 6C40DF5F0B497347."""
    return CRC(64, 0x42F0E1EBA9EA3693, 0, False, 0, "crc64_ecma")
