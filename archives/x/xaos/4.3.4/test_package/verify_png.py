#!/usr/bin/env python3
"""Decode the XaoS smoke PNG with only Python's standard library."""

import struct
import sys
import zlib


def fail(message):
    raise SystemExit(f"PNG verification failed: {message}")


if len(sys.argv) != 4:
    fail("usage: verify_png.py <png> <expected-width> <expected-height>")

path = sys.argv[1]
expected_width, expected_height = map(int, sys.argv[2:])
with open(path, "rb") as image_file:
    payload = image_file.read()

if payload[:8] != b"\x89PNG\r\n\x1a\n":
    fail("invalid PNG signature")

offset = 8
header = None
palette = None
compressed = bytearray()
seen_iend = False
while offset + 12 <= len(payload):
    size = struct.unpack_from(">I", payload, offset)[0]
    kind = payload[offset + 4 : offset + 8]
    start = offset + 8
    end = start + size
    if end + 4 > len(payload):
        fail("truncated PNG chunk")
    chunk = payload[start:end]
    if kind == b"IHDR":
        if size != 13:
            fail("invalid IHDR size")
        header = struct.unpack(">IIBBBBB", chunk)
    elif kind == b"PLTE":
        palette = chunk
    elif kind == b"IDAT":
        compressed.extend(chunk)
    elif kind == b"IEND":
        seen_iend = True
        offset = end + 4
        break
    offset = end + 4

if header is None or not seen_iend or not compressed:
    fail("missing IHDR, IDAT, or IEND")

width, height, bit_depth, color_type, compression, filtering, interlace = header
if (width, height) != (expected_width, expected_height):
    fail(f"expected {expected_width}x{expected_height}, got {width}x{height}")
if bit_depth != 8 or color_type not in (0, 2, 3, 4, 6):
    fail(f"unsupported PNG format: bit depth {bit_depth}, color type {color_type}")
if compression != 0 or filtering != 0 or interlace != 0:
    fail("unsupported PNG compression/filter/interlace mode")
if color_type == 3 and (palette is None or len(palette) % 3):
    fail("indexed PNG has an invalid palette")

channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color_type]
bytes_per_pixel = channels
stride = width * channels
try:
    scanlines = zlib.decompress(compressed)
except zlib.error as error:
    fail(f"IDAT zlib stream cannot be decoded: {error}")

if len(scanlines) != height * (stride + 1):
    fail("decoded scanline size does not match the image dimensions")

previous = bytearray(stride)
unique_pixels = set()
cursor = 0
for _row in range(height):
    filter_type = scanlines[cursor]
    current = bytearray(scanlines[cursor + 1 : cursor + stride + 1])
    cursor += stride + 1
    if filter_type not in (0, 1, 2, 3, 4):
        fail(f"invalid PNG row filter {filter_type}")
    for index in range(stride):
        left = current[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
        above = previous[index]
        upper_left = previous[index - bytes_per_pixel] if index >= bytes_per_pixel else 0
        if filter_type == 1:
            current[index] = (current[index] + left) & 0xFF
        elif filter_type == 2:
            current[index] = (current[index] + above) & 0xFF
        elif filter_type == 3:
            current[index] = (current[index] + ((left + above) // 2)) & 0xFF
        elif filter_type == 4:
            estimate = left + above - upper_left
            distances = (abs(estimate - left), abs(estimate - above), abs(estimate - upper_left))
            predictor = (left, above, upper_left)[distances.index(min(distances))]
            current[index] = (current[index] + predictor) & 0xFF
    unique_pixels.update(
        bytes(current[index : index + channels])
        for index in range(0, stride, channels)
    )
    previous = current

if len(unique_pixels) < 2:
    fail("rendered image has uniform pixel values")

sys.stdout.write(
    f"PNG_OK path={path} size={width}x{height} color_type={color_type} "
    f"unique_pixels_at_least={len(unique_pixels)} bytes={len(payload)}"
    "\n"
)
