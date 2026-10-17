#!/usr/bin/env python3
"""Programmatically generate a minimal, valid MPEG-2 Program Stream fixture.

No binary blob is committed: this generator emits an auditable, byte-exact
MPEG-2 PS that mpegdemux can scan / list / demux / remux deterministically.

Layout (43 bytes):
  [ 0..13] MPEG-2 pack header   (0x000001BA + 10 bytes, 0 stuffing)
  [14..38] PES packet, sid=0xE0 (video), 16-byte payload 0xAA
  [39..42] MPEG end code        (0x000001B9)

The pack header byte layout (verified against mpegdemux's mpegd_parse_pack):
  00 00 01 BA 44 00 04 00 04 01 00 00 03 F8
  - bits[32:34]='01'        -> MPEG-2 pack (parser elif branch)
  - bits[32:36]!=0x02       -> not MPEG-1
  - mux_rate (bits[80:102]) = 0
  - pack_stuffing (bits[109:112]) = 0  -> size = 14

The PES packet (mpegd_parse_packet, sid 0xE0 in [0xc0,0xf0)):
  00 00 01 E0 00 13 80 00 00  AA AA ... (x16)
  - PES_packet_length = 0x0013 (19) -> packet.size = 19 + 6 = 25
  - flags1=0x80 (10xxxxxx, pts_dts_flags=00) -> no PTS/DTS
  - PES_header_data_length = 0 -> packet.offset = 9
  - payload = 25 - 9 = 16 bytes of 0xAA

End code: 00 00 01 B9 (MPEG_END_CODE, mpegd_parse advances 4, end_cnt++).
"""
import sys


def build_fixture() -> bytes:
    # MPEG-2 pack header, 0 stuffing, all SCR/mux_rate zero
    pack = bytes([0x00, 0x00, 0x01, 0xBA,
                  0x44, 0x00, 0x04, 0x00,
                  0x04, 0x01, 0x00, 0x00,
                  0x03, 0xF8])

    payload = bytes([0xAA] * 16)

    # PES: start(3) + sid(1) + length(2) + flags1(1) + flags2(1) + hdrlen(1) + payload
    pes_len = 3 + len(payload)  # flags1+flags2+hdrlen + payload
    pes = bytes([0x00, 0x00, 0x01, 0xE0,
                 (pes_len >> 8) & 0xFF, pes_len & 0xFF,
                 0x80, 0x00, 0x00]) + payload

    end = bytes([0x00, 0x00, 0x01, 0xB9])

    data = pack + pes + end
    assert len(pack) == 14
    assert len(pes) == 6 + 3 + len(payload) == 25
    assert len(end) == 4
    assert len(data) == 43
    return data


def main() -> int:
    if len(sys.argv) != 2:
        sys.stderr.write("usage: gen_fixture.py <output.mpg>\n")
        return 2
    data = build_fixture()
    with open(sys.argv[1], "wb") as f:
        f.write(data)
    sys.stdout.write(f"generated {sys.argv[1]} ({len(data)} bytes)\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
