"""Create two deterministic DMS tracks: stored bytes and RLE bytes."""
import struct
import sys
from pathlib import Path


def crc16(data):
    crc = 0
    for byte in data:
        crc ^= byte
        for _ in range(8):
            crc = (crc >> 1) ^ (0xA001 if crc & 1 else 0)
    return crc


def track(number, packed, unpacked, mode):
    header = bytearray(20)
    header[:2] = b"TR"
    struct.pack_into(">H", header, 2, number)
    for offset, size in ((6, len(packed)), (8, len(packed)), (10, len(unpacked))):
        struct.pack_into(">H", header, offset, size)
    header[13] = mode
    struct.pack_into(">H", header, 14, sum(unpacked) & 0xffff)
    struct.pack_into(">H", header, 16, crc16(packed))
    struct.pack_into(">H", header, 18, crc16(header[:18]))
    return header + packed


raw = bytes((i * 37 + i // 97) % 256 for i in range(8192))
rle = bytes([0x90, 255, 0x5a, 32, 0])  # repeat 'Z' 0x2000 times
header = bytearray(52)
struct.pack_into(">H", header, 14, 1)  # final track
struct.pack_into(">H", header, 50, crc16(header[:50]))
Path(sys.argv[1]).write_bytes(
    b"DMS!" + header + track(0, raw, raw, 0) + track(1, rle, b"Z" * 8192, 1)
)
