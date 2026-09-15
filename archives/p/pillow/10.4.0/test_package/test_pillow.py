#!/usr/bin/env python3
"""Functional test for pillow 10.4.0 (R34: must exercise the package API).

Verifies:
  1. PIL imports (C extension .so files load on OHOS)
  2. version check
  3. image creation + pixel access (core _imaging extension)
  4. PNG round trip (zlib compression)
  5. JPEG write/read (libjpeg feature)
  6. ImageFont freetype rendering (freetype feature)
"""
import io
import os
import tempfile

from PIL import Image, ImageFont, features

print("Test 1 PASS: PIL imported successfully")

import PIL
assert PIL.__version__ == "10.4.0", f"Expected 10.4.0, got {PIL.__version__}"
print(f"Test 2 PASS: pillow version {PIL.__version__}")

img = Image.new("RGB", (8, 8), (255, 0, 0))
assert img.getpixel((4, 4)) == (255, 0, 0), "pixel access failed"
img.putpixel((0, 0), (0, 255, 0))
assert img.getpixel((0, 0)) == (0, 255, 0), "putpixel failed"
print("Test 3 PASS: image creation and pixel access work")

buf = io.BytesIO()
img.save(buf, format="PNG")
buf.seek(0)
img2 = Image.open(buf)
assert img2.size == (8, 8), "PNG round trip size mismatch"
assert img2.getpixel((4, 4)) == (255, 0, 0), "PNG pixel mismatch"
assert features.check("zlib") is True, "zlib feature missing"
print("Test 4 PASS: PNG round trip works (zlib)")

_tmpdir = tempfile.mkdtemp()
tmp = os.path.join(_tmpdir, "t.jpg")
img.save(tmp, format="JPEG")
img3 = Image.open(tmp)
assert img3.size == (8, 8), "JPEG round trip size mismatch"
# Image.open is lazy: force decode to actually exercise the libjpeg
# decoder path (jpeg_read_scanlines), not just the SOF header parse.
r, g, b = img3.convert("RGB").getpixel((4, 4))
assert abs(r - 255) <= 30 and g <= 60 and b <= 60, \
    f"JPEG decode produced wrong pixels: {(r, g, b)}"
assert features.check("jpg") is True, "libjpeg feature missing"
print("Test 5 PASS: JPEG round trip works (libjpeg)")

assert features.check("freetype2") is True, "freetype2 feature missing"
# Use a system font (no binary blob in the repo — GitCode PR diffs cannot
# carry binary blobs reliably, which blocked CI checkout 10+ times).
# /system/fonts ships with OHOS on both devices and CI workers.
def _find_system_font():
    candidates = [
        "/system/fonts/FTAeroSans-Regular.ttf",
        "/system/fonts/FTChariSans.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ]
    for cand in candidates:
        if os.path.isfile(cand):
            return cand
    import glob
    for cand in sorted(glob.glob("/system/fonts/*.ttf")):
        return cand
    raise AssertionError("no system ttf font found for freetype rendering test")

font_path = _find_system_font()
font = ImageFont.truetype(font_path, 16)
img4 = Image.new("L", (48, 24), 255)
from PIL import ImageDraw
draw = ImageDraw.Draw(img4)
draw.text((2, 2), "Hi", font=font, fill=0)
# rendered glyph pixels must darken some pixels
hist = img4.histogram()
assert sum(hist[:128]) > 0, "freetype text rendering produced no glyph pixels"
print("Test 6 PASS: freetype text rendering works")

print("All tests passed!")

import shutil
shutil.rmtree(_tmpdir, ignore_errors=True)
