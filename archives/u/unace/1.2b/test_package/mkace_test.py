#!/usr/bin/env python3
"""Build a minimal ACE v1.0 archive (stored entries) for the unace test_package.

Header layout follows unace 1.2b sources (read_header in unace.c, acestruc.h):
  header = HEAD_CRC(2, LE) + HEAD_SIZE(2, LE) + body
  body   = HEAD_TYPE(1) + HEAD_FLAGS(2) + [ADDSIZE(4) if flags & 1] + ...
  HEAD_CRC = getcrc(0xFFFFFFFF, body, HEAD_SIZE) & 0xffff
  file CRC32 = getcrc(0xFFFFFFFF, data, SIZE), the reflection-table CRC32
  without final XOR, i.e. zlib.crc32(data) ^ 0xFFFFFFFF.
"""
import struct
import sys
import zlib

ACESIGN = b"**ACE**"


def getcrc(crc, data):
    """unace getcrc: reflection CRC32 from the given seed, no final XOR."""
    crc ^= 0xFFFFFFFF
    crc = zlib.crc32(data, crc)
    return crc ^ 0xFFFFFFFF


def ts(y, m, d, h, n, s):
    return (((y - 1980) << 25) + (m << 21) + (d << 16) + (h << 11) + (n << 5) + (s // 2)) & 0xFFFFFFFF


def header(body, addsize=None):
    flags = struct.unpack_from("<H", body, 1)[0]
    if addsize is not None:
        flags |= 1  # ACE_ADDSIZE: skipsize for the data block that follows
        body = body[:3] + struct.pack("<I", addsize) + body[7:]
        body = body[:1] + struct.pack("<H", flags) + body[3:]
    crc = getcrc(0xFFFFFFFF, body) & 0xFFFF
    return struct.pack("<HH", crc, len(body)) + body


def main_header():
    body = bytearray()
    body += bytes([0])                        # HEAD_TYPE = MAIN_BLK
    body += struct.pack("<H", 0)              # HEAD_FLAGS: no AV/COMM/SOLID/volumes
    body += ACESIGN
    body += bytes([10, 10, 0, 0])             # VER_MOD VER_CR HOST_CR VOL_NUM
    body += struct.pack("<IHHI", ts(2004, 1, 1, 0, 0, 0), 0, 0, 0)
    body += bytes([0])                        # AV_SIZE = 0
    return header(bytes(body))


def file_header(fname, data, ftime):
    fb = bytearray()
    fb += bytes([1])                          # HEAD_TYPE = FILE_BLK
    fb += struct.pack("<H", 1)                # HEAD_FLAGS = ACE_ADDSIZE (patched below)
    fb += struct.pack("<I", len(data))        # ADDSIZE placeholder
    fb += struct.pack("<IIIII", len(data), len(data), ftime, 0,
                      getcrc(0xFFFFFFFF, data))  # PSIZE SIZE FTIME ATTR CRC32
    fb += bytes([0, 0])                       # TECH.TYPE = TYPE_STORE, TECH.QUAL
    fb += struct.pack("<HH", 0, 0)            # TECH.PARM, RESERVED
    fb += struct.pack("<H", len(fname))
    fb += fname
    return header(bytes(fb), addsize=len(data))


def main():
    out = sys.argv[1]
    ftime = ts(2026, 9, 21, 12, 0, 0)
    files = [
        (b"hello.txt", b"Hello from unace test package!\n"),
        (b"sub" + b"\\" + b"deep.txt", b"nested content for unace on OHOS\n"),
    ]
    blob = bytearray(main_header())
    for fname, data in files:
        blob += file_header(fname, data, ftime)
        blob += data  # stored: payload equals the raw content
    with open(out, "wb") as f:
        f.write(blob)
    print("written", out, len(blob), "bytes")


if __name__ == "__main__":
    main()
