#!/usr/bin/env python3
"""Build a minimal, spec-legal Windows index.dat (IE "Client Indexed Store") file
that pasco can parse. Field offsets/sizes taken from src/pasco.c (20040505):

  header   0x18  4B  version string (atof -> "5.2" => filever=5.2)
  header   0x1C  4B  filesize          (bah_to_i, little endian u32)
  header   0x20  4B  first hash-table offset (u32)
  hash     +0    4B  signature (pasco does not check it)
  hash     +4    4B  table size in 0x80 blocks
  hash     +8    4B  next hash-table offset (0 terminates the chain)
  hash     +16.. 8B entries: +0 flags u32 (low byte must != 0x03), +4 record offset u32
  record   +0    4B  type ("URL ", "LEAK", "REDR")
  record   +4    4B  record length in 0x80 blocks
  record   +8    8B  modified time  (FILETIME; all-zero => pasco prints empty field)
  record   +16   8B  access time    (FILETIME; ditto)
  record   0x34  1B  url offset relative to record start (used when filever >= 5)
  record   0x38  1B  dirname index  (used when filever >= 5.2)
  record   0x3C  4B  filename offset (absolute = u32 + record start; 0 => field skipped)
  record   0x44  4B  http-headers offset (absolute = u32 + record start; 0 => skipped)
"""
import struct
import sys

BLOCK = 0x80
URL = b"http://example.com/index.html"


def le32(v: int) -> bytes:
    return struct.pack("<I", v)


def build() -> bytes:
    filesize = 0x300
    hashoff = 0x100
    recoff = 0x200
    urloff = 0x50                      # record-relative, must fit in one byte

    buf = bytearray(filesize)

    # header block (0x00 - 0x4F)
    buf[0x00:0x14] = b"Client Indexed Store\x00" + b"\x00" * 2
    buf[0x18:0x1C] = b"5.2\x00"
    buf[0x1C:0x20] = le32(filesize)
    buf[0x20:0x24] = le32(hashoff)

    # hash table: 1 block, chain terminated by next=0
    buf[hashoff + 0:hashoff + 4] = b"HTSH"
    buf[hashoff + 4:hashoff + 8] = le32(1)
    buf[hashoff + 8:hashoff + 12] = le32(0)
    buf[hashoff + 16:hashoff + 20] = le32(0x00000001)   # flags, low byte != 0x03
    buf[hashoff + 20:hashoff + 24] = le32(recoff)

    # URL activity record
    buf[recoff + 0:recoff + 4] = b"URL "
    buf[recoff + 4:recoff + 8] = le32(1)                # one 0x80 block
    buf[recoff + 0x34] = urloff
    buf[recoff + 0x38] = 0xFF                           # dirname index out of range -> empty
    buf[recoff + urloff:recoff + urloff + len(URL)] = URL
    buf[recoff + urloff + len(URL)] = 0x00
    return bytes(buf)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.stderr.write("usage: gen_index_dat.py <output-file>\n")
        sys.exit(2)
    data = build()
    with open(sys.argv[1], "wb") as fh:
        fh.write(data)
    sys.stdout.write("wrote %s (%d bytes)\n" % (sys.argv[1], len(data)))
