#!/usr/bin/env python3
"""Helpers for the madplay 0.15.2b Conan consumer test.

All expectations below were verified against a real on-device
(aarch64-unknown-linux-ohos, musl) madplay run:

  * wave output: canonical 44-byte header (RIFF/WAVE + 16-byte fmt PCM16 +
    data), then FRAMES * 1152 samples, 16-bit little-endian mono 44100 Hz.
  * libmad's default dither keeps a silent MPEG stream within |x| <= 2
    (peak amplitude about -80 dB) — never exact silence.
  * hex output: one header line "# 1 channel, 44100 Hz, 24-bit samples",
    then one 6-digit hex sample per line.
"""
import struct

# MPEG-1 Layer III, 44100 Hz, mono, 128 kbps, no padding:
#   frame length = floor(144 * 128000 / 44100) = 417 bytes
FRAME_LEN = 417
SAMPLES_PER_FRAME = 1152
WAVE_HEADER = 44


def check_wave(path, frames):
    with open(path, "rb") as fh:
        data = fh.read()
    assert data[:4] == b"RIFF", f"not RIFF: {data[:4]!r}"
    assert data[8:12] == b"WAVE", f"not WAVE: {data[8:12]!r}"
    fmt = data[12:36]
    assert fmt[:4] == b"fmt ", f"fmt chunk missing: {fmt[:4]!r}"
    tag, channels, rate, _byte_rate, _align, bits = struct.unpack("<HHIIHH", fmt[8:24])
    assert tag == 1, f"not PCM: {tag}"
    assert channels == 1, f"expected mono, got {channels}"
    assert rate == 44100, f"expected 44100 Hz, got {rate}"
    assert bits == 16, f"expected 16-bit, got {bits}"
    assert data[36:40] == b"data", f"data chunk missing: {data[36:40]!r}"
    pcm_len = len(data) - WAVE_HEADER
    assert pcm_len == frames * SAMPLES_PER_FRAME * 2, \
        f"PCM bytes {pcm_len} != {frames * SAMPLES_PER_FRAME * 2}"
    samples = struct.unpack(f"<{pcm_len // 2}h", data[WAVE_HEADER:])
    peak = max(abs(s) for s in samples)
    assert peak <= 2, f"silent stream peak {peak} exceeds dither noise"


def check_hex_dump(path, frames):
    with open(path) as fh:
        lines = fh.read().splitlines()
    assert lines and lines[0].startswith("# "), f"hex header missing: {lines[:1]!r}"
    assert "1 channel" in lines[0], f"expected mono header: {lines[0]!r}"
    assert "44100" in lines[0], f"expected 44100 Hz header: {lines[0]!r}"
    data_lines = lines[1:]
    assert len(data_lines) == frames * SAMPLES_PER_FRAME, \
        f"hex sample count {len(data_lines)} != {frames * SAMPLES_PER_FRAME}"
    for line in data_lines:
        v = int(line, 16)
        if v >= 0x800000:
            v -= 0x1000000
        assert abs(v) <= 2, f"silent stream hex sample out of dither range: {line}"
