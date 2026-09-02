#!/usr/bin/env python3
"""Generate deterministic PCM fixtures for the installed abx self-test."""

import math
from pathlib import Path
import struct
import sys
import wave


RATE = 8000
CHANNELS = 2
FRAMES = 800
AMPLITUDE = 16000


def write_tone(path: Path, frequency: float, frames: int) -> None:
    samples = bytearray()
    for index in range(frames):
        phase = 2.0 * math.pi * frequency * index / RATE
        sample = int(AMPLITUDE * math.sin(phase))
        samples.extend(struct.pack("<hh", sample, -sample))

    with wave.open(str(path), "wb") as output:
        output.setnchannels(CHANNELS)
        output.setsampwidth(2)
        output.setframerate(RATE)
        output.writeframes(samples)


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: generate_wavs.py OUTPUT_DIRECTORY")
    output_dir = Path(sys.argv[1])
    output_dir.mkdir(parents=True, exist_ok=True)
    write_tone(output_dir / "sample-a.wav", 440.0, FRAMES)
    write_tone(output_dir / "sample-b.wav", 880.0, FRAMES)
    write_tone(output_dir / "sample-short.wav", 440.0, FRAMES // 2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
