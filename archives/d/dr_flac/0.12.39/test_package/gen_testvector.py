#!/usr/bin/env python3
"""Deterministic FLAC test-vector generator for the dr_flac 0.12.39 consumer test.

The upstream mackron/dr_libs 0.12.39 testvectors/flac/ directory ships EMPTY
(only DO_NOT_DELETE.md), so there is no official FLAC sample to decode. This
generator deterministically emits a structurally-valid, minimal FLAC stream
that exercises two of dr_flac's subframe decoders (CONSTANT and VERBATIM)
plus the multi-channel (independent) path and the frame CRC-8 / CRC-16
verification, so the consumer test performs REAL decode work.

File layout produced:
  "fLaC"
  + STREAMINFO metadata block (last=1, type=0, len=32)
  + one FLAC frame:
      sync(0xFF)+header + 2 subframes (ch0 CONSTANT, ch1 VERBATIM) + CRC-16

Parameters (kept identical between this generator and test_dr_flac.c):
  channels     = 2 (independent -> channel_assignment code 1)
  sample_rate  = 44100 (code 9 in dr_flac's sampleRateTable)
  bps          = 16    (3-bit dr_flac code 4)
  block_size   = 256   (code 8 -> 256 * (1 << (8-8)))
  frames       = 256
  ch0: CONSTANT, all samples = C0
  ch1: VERBATIM, sawtooth v[i] = (i*128) % 32768, sign-extended to [-16384,16383]

CRCs implemented exactly as dr_flac computes them:
  CRC-8 : poly 0x07, init 0, no reflection / no final XOR (MSB-first table)
  CRC-16: poly 0x8005, init 0, MSB-first, table built as crc=n<<8 (see
          drflac_crc16_byte / drflac__crc16_table). Frame CRC-16 covers the
          frame from the 0xFF sync byte through the last subframe byte,
          EXCLUDING the trailing 2-byte CRC-16 field.
"""
import hashlib
import math
import struct
import sys

# ---------------------------------------------------------------- CRC tables
def _crc8_table():
    t = []
    for n in range(256):
        c = n
        for _ in range(8):
            c = ((c << 1) ^ 0x07) if (c & 0x80) else (c << 1)
            c &= 0xFF
        t.append(c)
    return t

def _crc16_table():
    t = []
    for n in range(256):
        c = n << 8
        for _ in range(8):
            c = ((c << 1) ^ 0x8005) if (c & 0x8000) else (c << 1)
            c &= 0xFFFF
        t.append(c)
    return t

CRC8T = _crc8_table()
CRC16T = _crc16_table()

def crc8(data):
    c = 0
    for b in data:
        c = CRC8T[(c ^ b) & 0xFF]
    return c

def crc16(data):
    c = 0
    for b in data:
        c = ((c << 8) & 0xFFFF) ^ CRC16T[((c >> 8) ^ b) & 0xFF]
    return c

# ---------------------------------------------------------------- parameters
CHANNELS = 2
SAMPLE_RATE = 44100
BPS = 16
BLOCK_SIZE = 256
C0 = 12345  # constant subframe value (channel 0)

def ch1_samples():
    out = []
    for i in range(BLOCK_SIZE):
        v = (i * 128) % 32768
        out.append(v - 32768 if v >= 16384 else v)
    return out

# ---------------------------------------------------------------- STREAMINFO
def build_streaminfo(pcm_pcm_bytes):
    md5 = hashlib.md5(pcm_pcm_bytes).digest()
    out = b""
    out += struct.pack(">HH", BLOCK_SIZE, BLOCK_SIZE)          # min/max block (16+16 bits)
    out += b"\x00\x00\x00" + b"\x00\x00\x00"                    # min/max frame (24+24 bits)
    # sample rate(20) | channels-1(3) | bps-1(5) | total(36)  -> 64 bits
    sr = SAMPLE_RATE
    ch = CHANNELS - 1
    b = BPS - 1
    total = BLOCK_SIZE
    field = (sr << 44) | (ch << 41) | (b << 36) | total
    out += struct.pack(">Q", field)
    out += md5
    assert len(out) == 34, len(out)   # STREAMINFO is 34 bytes
    return out

# ---------------------------------------------------------------- frame
def be16(v):
    return struct.pack(">H", v & 0xFFFF)

def build_frame():
    header = b""
    header += b"\xFF"            # sync high byte
    # byte1: sync-low6 (0x3E) | reserved(0) | blocking(0) = 111110 00 = 0xF8
    header += bytes([0xF8])
    # byte2: blockSize code(8) | sampleRate code(9) = 1000 1001 = 0x89
    header += bytes([0x89])
    # byte3: channelAssignment(1) | bps code(4) | reserved(0) = 0001 1000 = 0x18
    header += bytes([0x18])
    # byte4: flac frame number = 0 (fixed strategy)
    header += bytes([0x00])
    c8 = crc8(header)          # CRC-8 over the 5 header bytes before the CRC field
    header += bytes([c8])      # 8-bit frame header CRC-8 (1 byte)

    data = b""
    # channel 0: CONSTANT subframe
    data += bytes([0x00])                 # header: bit7=0, type=0, wasted=0
    data += be16(C0)                       # single constant sample
    # channel 1: VERBATIM subframe
    data += bytes([0x02])                 # header: bit7=0, type=1, wasted=0
    for s in ch1_samples():
        data += be16(s)

    body = header + data
    c16 = crc16(body)
    return body + struct.pack(">H", c16)

def main():
    # raw decoded PCM (interleaved, 16-bit big-endian) for the STREAMINFO MD5
    pcm = b""
    s1 = ch1_samples()
    for i in range(BLOCK_SIZE):
        pcm += be16(C0) + be16(s1[i])

    streaminfo = build_streaminfo(pcm)
    frame = build_frame()

    # STREAMINFO block header: last=1, type=0, length=34 (0x22)
    blob = b"fLaC" + b"\x80\x00\x00\x22" + streaminfo + frame

    sys.stdout.write("=== generated FLAC (%d bytes) ===\n" % len(blob))
    hd = blob[:64]
    print(" ".join("%02X" % x for x in hd))
    print("...")
    print("SHA256:", hashlib.sha256(blob).hexdigest())
    print("frame header CRC8  = %02X (computed)" % crc8(frame[:5]))
    print("frame CRC16        = %04X (computed)" % crc16(frame[:-2]))
    print("md5(decoded pcm)   = %s" % hashlib.md5(pcm).hexdigest())

    out_h = "flac_test_vector.h"
    with open(out_h, "w") as f:
        f.write("// AUTO-GENERATED by gen_testvector.py -- do not edit by hand.\n")
        f.write("// Deterministic 2-channel FLAC test vector for dr_flac 0.12.39.\n")
        f.write("//  ch0 = CONSTANT(%d) x %d, ch1 = VERBATIM sawtooth x %d, %d Hz, %d bps\n"
                % (C0, BLOCK_SIZE, BLOCK_SIZE, SAMPLE_RATE, BPS))
        f.write("static const unsigned char g_testFlac[] = {\n")
        for i in range(0, len(blob), 12):
            row = blob[i:i + 12]
            f.write("    " + ", ".join("0x%02X" % x for x in row) + ",\n")
        f.write("};\n")
        f.write("static const unsigned int g_testFlacSize = %d;\n" % len(blob))
        f.write("static const int g_testChannels = %d;\n" % CHANNELS)
        f.write("static const unsigned int g_testFrames = %d;\n" % BLOCK_SIZE)
        f.write("static const int g_testConstant0 = %d;\n" % C0)
    print("wrote", out_h, "(%d bytes of FLAC)" % len(blob))

if __name__ == "__main__":
    main()
