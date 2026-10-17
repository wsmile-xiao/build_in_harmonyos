#!/usr/bin/env python3
"""Conan test_package — unzoo 4.4.

unzoo ships no tests at all, so this is a real round trip assembled here:

  1. a spec-valid zoo archive is generated (42-byte archive descriptor, one
     directory entry with a *stored* member and its CRC-16, and the
     posnxt == 0 terminator entry that ends the directory walk);
  2. the installed ``unzoo`` lists it (``-l``);
  3. the installed ``unzoo`` extracts it (``-x``);
  4. the extracted bytes are compared with the original payload.

Step 3 is meaningful rather than a smoke test because unzoo prints
"extracted ..." only when the member's CRC-16 matches what the entry declares;
a mismatch prints "error, CRC failed" instead.  So the check also exercises the
CRC path.

Archive format notes (all taken from the structure declarations and the
DescReadArch/EntrReadArch readers in unzoo.c):
  * multi-byte fields are little-endian (WordReadArch shifts byte 0 into bits
    0-7);
  * the directory walk in main() runs until it reads an entry whose
    ``posnxt`` is 0 — an archive without that terminator is reported as
    "found bad directory entry";
  * an entry is 51 bytes when ``type != 2`` (type 2 carries the variable part
    with the long name and directory);
  * ``method == 0`` means the member is stored uncompressed, and extraction
    seeks to ``posdat`` and copies ``siznow`` bytes;
  * an entry with ``majver == 2`` and ``minver > 1`` is refused as
    "unknown method, you need a later version", so minver is 0.
"""
import os
import struct

from conan import ConanFile

PAYLOAD = b"unzoo round-trip payload 0123456789\n"
MEMBER = "HELLO.TXT"
ZOO_MAGIC = 0xFDC4A7DC


def _crc_table():
    table = []
    for i in range(256):
        value = i
        for _ in range(8):
            value = (value >> 1) ^ 0xA001 if value & 1 else value >> 1
        table.append(value)
    return table


_CRC_TABLE = _crc_table()


def crc16(data):
    """unzoo's CRC_BYTE: reflected CRC-16, poly 0xA001, init 0, no final xor."""
    crc = 0
    for byte in data:
        crc = (crc >> 8) ^ _CRC_TABLE[(crc ^ byte) & 0xFF]
    return crc & 0xFFFF


def build_zoo(name, data):
    """Build a minimal zoo archive holding one stored member."""
    terminator_len = 51

    descriptor = b"ZOO 2.10 Archive.\x1aZ".ljust(20, b"\x00")[:20]
    descriptor += struct.pack("<I", ZOO_MAGIC)        # magic
    descriptor += struct.pack("<I", 42)               # posent: first entry
    descriptor += struct.pack("<I", (-42) & 0xFFFFFFFF)  # klhvmh
    descriptor += bytes([2, 0])                       # majver, minver
    descriptor += bytes([1])                          # type
    descriptor += struct.pack("<I", 0)                # poscmt
    descriptor += struct.pack("<H", 0)                # sizcmt
    descriptor += bytes([0])                          # modgen
    assert len(descriptor) == 42, len(descriptor)

    entry_len = 51
    posdat = 42 + entry_len
    posnxt = posdat + len(data)

    entry = struct.pack("<I", ZOO_MAGIC)              # magic
    entry += bytes([1])                               # type 1 -> no variable part
    entry += bytes([0])                               # method 0 -> stored
    entry += struct.pack("<I", posnxt)                # position of next member
    entry += struct.pack("<I", posdat)                # position of data
    entry += struct.pack("<H", 0)                     # datdos
    entry += struct.pack("<H", 0)                     # timdos
    entry += struct.pack("<H", crc16(data))           # crcdat
    entry += struct.pack("<I", len(data))             # sizorg
    entry += struct.pack("<I", len(data))             # siznow
    entry += bytes([2, 0])                            # majver, minver
    entry += bytes([0, 0])                            # delete, spared
    entry += struct.pack("<I", 0)                     # poscmt
    entry += struct.pack("<H", 0)                     # sizcmt
    entry += name.encode()[:13].ljust(13, b"\x00")    # nams
    assert len(entry) == entry_len, len(entry)

    # Terminator: the walk stops when it reads an entry with posnxt == 0.
    terminator = struct.pack("<I", ZOO_MAGIC) + bytes([0, 0]) + struct.pack("<I", 0)
    terminator = terminator.ljust(terminator_len, b"\x00")
    assert len(terminator) == terminator_len, len(terminator)

    return descriptor + entry + data + terminator


class UnzooTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Fixture setup: one spec-valid zoo archive.  Building it needs the
        # CRC-16 and the little-endian directory-entry layout, so it stays in
        # Python; the assertions live in test.sh (POSIX sh) and run against the
        # installed CLI.
        archive = os.path.join(self.build_folder, "good.zoo")
        with open(archive, "wb") as handle:
            handle.write(build_zoo(MEMBER, PAYLOAD))

        script = os.path.join(self.recipe_folder, "test.sh")
        # test.sh exits non-zero on the first failed assertion, which makes
        # self.run() raise.
        self.run('sh "{}" "{}"'.format(script, self.build_folder),
                 env="conanrun")
