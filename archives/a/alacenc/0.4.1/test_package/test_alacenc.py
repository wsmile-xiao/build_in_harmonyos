"""Helpers used by the alacenc Conan consumer smoke test."""

import math
import os
import struct
import wave


def write_wav(path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sample_rate = 8000
    frames = []
    for index in range(sample_rate // 10):
        sample = int(16000 * math.sin(2.0 * math.pi * 440.0 * index / sample_rate))
        frames.append(struct.pack("<h", sample))
    with wave.open(path, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"".join(frames))


def verify_m4a(path):
    if not os.path.exists(path):
        raise AssertionError("alacenc did not create output.m4a")
    if os.path.getsize(path) <= 32:
        raise AssertionError("encoded output is unexpectedly small")
    with open(path, "rb") as handle:
        header = handle.read(16)
    if b"ftyp" not in header:
        raise AssertionError("encoded output does not look like an M4A/MP4 file")
