"""Helpers used by the mppenc Conan consumer smoke test."""

import math
import os
import struct
import wave

ASSERTION_COUNT = 4


def write_wav(path):
    """Generate a 44.1 kHz mono 16-bit PCM WAV fixture.

    mppenc supports 32/37.8/44.1/48 kHz sample rates; 0.1 s of 440 Hz sine.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    sample_rate = 44100
    frames = []
    for index in range(sample_rate // 10):
        sample = int(16000 * math.sin(2.0 * math.pi * 440.0 * index / sample_rate))
        frames.append(struct.pack("<h", sample))
    with wave.open(path, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        wav.writeframes(b"".join(frames))


def verify_mpc(path):
    """Check the encoded Musepack file: SV7 'MP+' magic, stream version 7, sane size."""
    if not os.path.exists(path):
        raise AssertionError("mppenc did not create output.mpc")
    size = os.path.getsize(path)
    if not 32 < size < 100000:
        raise AssertionError("encoded output has unexpected size: %d" % size)
    with open(path, "rb") as handle:
        header = handle.read(4)
    # Musepack SV7 streams start with the 'MP+' magic followed by the stream version byte.
    if header[0:3] != b"MP+":
        raise AssertionError("encoded output does not carry the SV7 'MP+' header magic")
    if header[3] != 7:
        raise AssertionError("stream version byte is not 7 (got %d)" % header[3])
    print("[PASS] 3/4 output.mpc exists with sane size (%d bytes)" % size)
    print("[PASS] 4/4 output.mpc carries SV7 'MP+' magic, stream version 7")
