"""
Minimal crc16 implementation used across the repository.
Implements CRC-16/XMODEM (polynomial 0x1021).

API: crc16xmodem(data, init=0)
- data: bytes, bytearray, or str (will be encoded to latin-1)
- init: initial CRC value (default 0x0000)
Returns: integer CRC value (0-0xFFFF)

This module provides a drop-in replacement for the external 'crc16' module
that older code expects (used as `import crc16`).
"""
from __future__ import annotations

from typing import Union


def _to_bytes(data: Union[bytes, bytearray, str]) -> bytes:
    if isinstance(data, bytes):
        return data
    if isinstance(data, bytearray):
        return bytes(data)
    if isinstance(data, str):
        # Previously this code often used str(bytearray) in Python 2, which
        # returned raw bytes. In Python 3 str(bytearray) returns "bytearray(b'...')",
        # so best-effort: if it looks like that representation, extract inner bytes.
        if data.startswith("bytearray(b'") and data.endswith("')"):
            # extract the literal content
            inner = data[len("bytearray(b'"):-2]
            return inner.encode('latin-1')
        # Generic string: encode as latin-1 to preserve byte values 0-255
        return data.encode('latin-1')
    raise TypeError("crc16: data must be bytes, bytearray, or str")


def crc16xmodem(data: Union[bytes, bytearray, str], init: int = 0) -> int:
    """Compute CRC-16/XMODEM over data.

    Parameters
    - data: bytes/bytearray or string; string will be encoded with latin-1
    - init: initial CRC value (default 0x0000). Some callers pass 0xFFFF or 0.

    Returns
    - 16-bit integer CRC value
    """
    data_bytes = _to_bytes(data)
    crc_val = init & 0xFFFF
    poly = 0x1021
    for byte in data_bytes:
        crc_val ^= (byte << 8)
        for _ in range(8):
            if crc_val & 0x8000:
                crc_val = ((crc_val << 1) ^ poly) & 0xFFFF
            else:
                crc_val = (crc_val << 1) & 0xFFFF
    return crc_val


# Provide legacy name for convenience
crc = crc16xmodem


if __name__ == "__main__":
    # quick self-check: CRC of ASCII '123456789' should be 0x31C3 for XMODEM
    TEST = b'123456789'
    print(hex(crc16xmodem(TEST)))
