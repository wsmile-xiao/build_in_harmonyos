#!/usr/bin/env python3
"""Conan test_package — unlzx 1.1.

unlzx ships no tests at all, so this is a real round trip assembled here:

  1. a spec-valid LZX archive is generated (10-byte info header, the 31-byte
     Archive_Header with the header CRC that unlzx itself recomputes, one
     *stored* member and that member's data CRC);
  2. the installed ``unlzx`` lists it (``-v``) and extracts it (``-x``);
  3. the extracted bytes are compared with the original payload;
  4. an archive whose header CRC has been corrupted must be refused.

Step 3 is what makes this meaningful: it exercises the info-header check, the
archive-header CRC, the per-member data CRC and the extraction path — the
program "starts up" case is covered by step 4 only as a negative.

Package format notes (from the structure comments at the end of unlzx.c):
  * every multi-byte field is little-endian ("FUCKED UP LITTLE ENDIAN SHIT");
  * ``HDR_PACK_STORE == 0`` means the member is stored uncompressed;
  * the header CRC is CRC-32 over the 31 header bytes with its own CRC field
    zeroed, then the filename bytes, then the comment bytes.
"""
import os
import struct
import zlib

from conan import ConanFile

PAYLOAD = b"unlzx round-trip payload 0123456789\n"
MEMBER = "hello.txt"


def crc32(data, seed=0):
    """Same CRC-32 as unlzx's crc_calc (table starts 0, 0x77073096, 0xEE0E612C)."""
    return zlib.crc32(data, seed) & 0xFFFFFFFF


def build_lzx(name, data, corrupt_header_crc=False):
    """Build a minimal LZX archive holding one stored member."""
    name_b = name.encode()
    hdr = bytearray(31)
    hdr[2:6] = struct.pack("<I", len(data))      # unpacked size
    hdr[6:10] = struct.pack("<I", len(data))     # packed size == stored size
    hdr[10] = 20                                 # HDR_TYPE_UNIX
    hdr[11] = 0                                  # HDR_PACK_STORE
    hdr[12] = 0                                  # flags
    hdr[14] = 0                                  # comment length
    hdr[15] = 0                                  # version needed to extract
    hdr[18:22] = struct.pack("<I", 0)            # date
    hdr[22:26] = struct.pack("<I", crc32(data))  # data CRC
    hdr[26:30] = b"\0\0\0\0"                     # header CRC placeholder
    hdr[30] = len(name_b)

    header_crc = crc32(bytes(hdr), 0)
    header_crc = crc32(name_b, header_crc)
    if corrupt_header_crc:
        header_crc ^= 0xFFFFFFFF
    hdr[26:30] = struct.pack("<I", header_crc)

    return b"LZX\x00" + b"\0" * 6 + bytes(hdr) + name_b + data


class UnlzxTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _write(self, name, blob):
        with open(os.path.join(self.build_folder, name), "wb") as handle:
            handle.write(blob)

    def test(self):
        # Fixture setup: two LZX archives with the exact header CRC that unlzx
        # recomputes.  Building them needs struct+zlib CRC-32, so it stays in
        # Python; the assertions themselves live in test.sh (POSIX sh) and run
        # against the installed CLI.
        self._write("good.lzx", build_lzx(MEMBER, PAYLOAD))
        self._write("bad.lzx", build_lzx(MEMBER, PAYLOAD, corrupt_header_crc=True))

        script = os.path.join(self.recipe_folder, "test.sh")
        # test.sh exits non-zero on the first failed assertion, which makes
        # self.run() raise.
        self.run('sh "{}" "{}"'.format(script, self.build_folder),
                 env="conanrun")
