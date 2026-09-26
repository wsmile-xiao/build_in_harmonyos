#!/usr/bin/env python3
"""Generate a minimal, valid DMS archive for the xdms consumer test.

Why this exists
---------------
xdms is an *unpacker*; upstream ships no API to create DMS files, so there is
nothing in the package to call.  The test data is therefore built here, at test
time, from a plain-text recipe — **no binary blob is committed to the
repository**.  A committed binary cannot travel inside GitCode's
`/pull/<n>.diff`, which is exactly what the CI applies at its `checkout-pr`
step; carrying one made that step fail with:

    error: missing binary patch data for '.../sample.dms'
    error: binary patch does not apply to '.../sample.dms'

File layout follows xDMS's own reader (upstream `src/pfile.c`, xdms 1.3.2):

  * 56-byte main header:
        [0..3]   "DMS!" magic
        [4..53]  covered by the header CRC
        [54..55] CRC16, big-endian
    header CRC = CRC16 over bytes [4 .. 4+50) == [4..53]
  * 20-byte track header:
        [0..1]   "TR"
        [2..3]   track number (0)
        [6..7]   pklen1  (packed length in archive)
        [8..9]   pklen2  (length after first unpacking)
        [10..11] unpklen (length after RLE unpacking)
        [12]     flags
        [13]     cmode  (0 == NOCOMP)
        [14..15] checksum of the *unpacked* data, big-endian
        [16..17] CRC16 of the packed data, big-endian
        [18..19] CRC16 of bytes [0..18), big-endian
  * track payload

Only the standard library is used; the two hashes are reimplemented from
upstream `src/crc_csum.c` so the generator needs no compiler and no xdms source
tree:

  * `CreateCRC`      == CRC-16/ARC (reflected poly 0xA001, init 0, no final xor)
  * `Calc_CheckSum`  == sum of bytes truncated to 16 bits

Usage:  make_sample_dms.py <output-path>
"""
import sys

# The payload is deterministic so the shell test can rebuild it independently
# and compare byte-for-byte (see test_xdms.sh).
PAYLOAD_LINE = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ\n"
PAYLOAD_LEN = 3000          # must exceed 2048: pfile.c only decodes tracks with unpklen > 2048
HEADLEN = 56
THLEN = 20


def crc16(data):
    """CRC-16/ARC — upstream CreateCRC() in src/crc_csum.c."""
    crc = 0
    for b in data:
        crc ^= b
        for _ in range(8):
            crc = (crc >> 1) ^ 0xA001 if (crc & 1) else (crc >> 1)
    return crc & 0xFFFF


def checksum16(data):
    """Upstream Calc_CheckSum() in src/crc_csum.c — plain 16-bit byte sum."""
    return sum(data) & 0xFFFF


def build_payload():
    line = PAYLOAD_LINE.encode("ascii")
    return (line * (PAYLOAD_LEN // len(line) + 1))[:PAYLOAD_LEN]


def build():
    payload = build_payload()

    hdr = bytearray(HEADLEN)
    hdr[0:4] = b"DMS!"
    hdr[18:20] = (1).to_bytes(2, "big")          # highest track in archive
    hdr[21:24] = len(payload).to_bytes(3, "big")  # total packed size
    hdr[25:28] = len(payload).to_bytes(3, "big")  # total unpacked size
    hdr[46:48] = (100).to_bytes(2, "big")         # "created with DMS 1.00"
    hdr[50:52] = (0).to_bytes(2, "big")           # disk type
    hdr[52:54] = (0).to_bytes(2, "big")           # compression mode == NOCOMP
    hc = crc16(hdr[4:4 + HEADLEN - 6])
    hdr[54:56] = hc.to_bytes(2, "big")

    trk = bytearray(THLEN)
    trk[0:2] = b"TR"
    trk[2:4] = (0).to_bytes(2, "big")             # track number
    trk[6:8] = len(payload).to_bytes(2, "big")    # pklen1
    trk[8:10] = len(payload).to_bytes(2, "big")   # pklen2
    trk[10:12] = len(payload).to_bytes(2, "big")  # unpklen
    trk[12] = 0                                   # flags
    trk[13] = 0                                   # cmode == NOCOMP (memcpy path)
    trk[14:16] = checksum16(payload).to_bytes(2, "big")   # usum (post-unpack)
    trk[16:18] = crc16(payload).to_bytes(2, "big")        # dcrc (packed data)
    tc = crc16(trk[0:THLEN - 2])
    trk[18:20] = tc.to_bytes(2, "big")

    return bytes(hdr) + bytes(trk) + payload


def main(argv):
    if len(argv) != 2:
        print("usage: make_sample_dms.py <output-path>", file=sys.stderr)
        return 2
    blob = build()
    with open(argv[1], "wb") as f:
        f.write(blob)
    print(f"wrote {argv[1]} ({len(blob)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
