#!/usr/bin/env python3
"""Generate a deterministic FITS image containing synthetic Gaussian stars."""

import math
import struct
import sys
from pathlib import Path

WIDTH = 256
HEIGHT = 256
STARS = (
    (24, 31, 17000), (53, 45, 21000), (89, 28, 18000),
    (121, 57, 23000), (158, 35, 19000), (207, 52, 22000),
    (37, 91, 20000), (75, 118, 24000), (111, 93, 17500),
    (149, 126, 21500), (193, 101, 18500), (229, 122, 22500),
    (29, 161, 19500), (66, 190, 23500), (103, 153, 20500),
    (142, 184, 18000), (179, 158, 23000), (218, 196, 20000),
    (48, 224, 22000), (94, 213, 19000), (132, 231, 24000),
    (171, 217, 21000), (210, 232, 18000),
)


def card(keyword, value=None, comment=None):
    if value is None:
        text = keyword
    else:
        rendered = "T" if value is True else "F" if value is False else str(value)
        text = f"{keyword:<8}= {rendered:>20}"
        if comment:
            text += f" / {comment}"
    return text[:80].ljust(80)


def main():
    output = Path(sys.argv[1])
    cards = [
        card("SIMPLE", True, "conforms to FITS standard"),
        card("BITPIX", 16),
        card("NAXIS", 2),
        card("NAXIS1", WIDTH),
        card("NAXIS2", HEIGHT),
        card("BZERO", 0),
        card("BSCALE", 1),
        card("END"),
    ]
    header = "".join(cards).encode("ascii")
    header += b" " * ((-len(header)) % 2880)

    pixels = []
    for y in range(HEIGHT):
        for x in range(WIDTH):
            value = 900 + ((x * 17 + y * 29) % 23)
            for sx, sy, peak in STARS:
                distance2 = (x - sx) ** 2 + (y - sy) ** 2
                if distance2 <= 36:
                    value += int(peak * math.exp(-distance2 / 4.5))
            pixels.append(min(value, 32000))
    data = struct.pack(f">{len(pixels)}h", *pixels)
    data += b"\0" * ((-len(data)) % 2880)
    output.write_bytes(header + data)


if __name__ == "__main__":
    main()
