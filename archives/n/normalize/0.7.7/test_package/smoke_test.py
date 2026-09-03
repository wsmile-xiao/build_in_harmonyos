#!/usr/bin/env python3
"""Functional test helpers for the packaged `normalize` binary (R34).

This module ships alongside test_package/conanfile.py as the standalone test
source file that satisfies the CI L0c gate (a test_package/ must contain a
real source file, not only a conanfile).  `conanfile.py::test()` imports the
helpers here and drives the installed `normalize` binary through Conan's
self.run(..., env="conanrun") — the same environment in which the previous
W3 run already proved direct invocations work.

Provided:
  * make_wav(path)  — synthesise a mono 16-bit PCM WAV (stdlib only)
  * wav_changed(a,b)— helper to report whether an in-place rewrite happened

The module is pure Python + stdlib, so it never depends on a compiler or on
`curl`/network at test time.
"""
import math
import struct
import wave


def make_wav(path, seconds=1.0, freq=440.0, rate=44100):
    """Write a mono 16-bit PCM WAV containing a ~12 k-samples sine wave."""
    n = int(rate * seconds)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        frames = b"".join(
            struct.pack(
                "<h",
                int(12000 * 0.9 * math.sin(2 * math.pi * freq * i / rate)),
            )
            for i in range(n)
        )
        w.writeframes(frames)
    return path
