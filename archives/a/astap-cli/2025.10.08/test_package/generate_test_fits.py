#!/usr/bin/env python3
import math
import struct
import sys
from pathlib import Path

W = H = 256
STARS = [(24, 31, 17000), (53, 45, 21000), (89, 28, 18000), (121, 57, 23000), (158, 35, 19000), (207, 52, 22000), (37, 91, 20000), (75, 118, 24000), (111, 93, 17500), (149, 126, 21500), (193, 101, 18500), (229, 122, 22500), (29, 161, 19500), (66, 190, 23500), (103, 153, 20500), (142, 184, 18000), (179, 158, 23000), (218, 196, 20000), (48, 224, 22000), (94, 213, 19000), (132, 231, 24000), (171, 217, 21000), (210, 232, 18000)]

def card(name, value=None):
    return (name if value is None else f"{name:<8}= {str(value):>20}").ljust(80)

def main():
    output = Path(sys.argv[1])
    header = b"".join((card("SIMPLE", "T").encode(), card("BITPIX", 16).encode(), card("NAXIS", 2).encode(), card("NAXIS1", W).encode(), card("NAXIS2", H).encode(), card("END").encode()))
    header += b" " * ((-len(header)) % 2880)
    pixels = []
    for y in range(H):
        for x in range(W):
            value = 900 + ((x * 17 + y * 29) % 23)
            for sx, sy, peak in STARS:
                distance2 = (x - sx) ** 2 + (y - sy) ** 2
                if distance2 <= 36:
                    value += int(peak * math.exp(-distance2 / 4.5))
            pixels.append(min(value, 32000))
    data = struct.pack(f">{len(pixels)}h", *pixels)
    output.write_bytes(header + data + b"\0" * ((-len(data)) % 2880))

if __name__ == "__main__":
    main()
