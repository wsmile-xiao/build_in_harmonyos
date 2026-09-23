#!/usr/bin/env python3
"""Independent consumers of the installed KDE Breeze GRUB resources."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import struct
import unittest
import xml.etree.ElementTree as ET
import zlib

HERE = Path(__file__).resolve().parent
EXPECTED = json.loads((HERE / "expected.json").read_text(encoding="utf-8"))
PACKAGE = None


def png_info(raw):
    if raw[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("Invalid PNG signature")
    pos, chunks, compressed = 8, [], bytearray()
    while pos < len(raw):
        size, = struct.unpack_from(">I", raw, pos)
        kind = raw[pos + 4:pos + 8]
        body = raw[pos + 8:pos + 8 + size]
        crc, = struct.unpack_from(">I", raw, pos + 8 + size)
        if len(body) != size or zlib.crc32(kind + body) != crc:
            raise ValueError("PNG chunk CRC mismatch")
        chunks.append(kind)
        if kind == b"IHDR":
            width, height, depth, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", body)
            if not width or not height or compression or filtering or interlace:
                raise ValueError("Unexpected PNG layout")
        if kind == b"IDAT":
            compressed.extend(body)
        pos += size + 12
        if kind == b"IEND":
            break
    if chunks[0] != b"IHDR" or chunks[-1] != b"IEND" or pos != len(raw):
        raise ValueError("Incomplete PNG")
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color]
    stride = (width * channels * depth + 7) // 8
    pixels = zlib.decompress(compressed)
    if len(pixels) != height * (stride + 1):
        raise ValueError("Invalid decompressed PNG length")
    if any(pixels[y * (stride + 1)] > 4 for y in range(height)):
        raise ValueError("Invalid PNG scanline filter")
    return width, height


def pf2_info(raw):
    pos, sections = 0, {}
    while pos + 8 <= len(raw):
        kind = raw[pos:pos + 4]
        size, = struct.unpack_from(">I", raw, pos + 4)
        pos += 8
        if kind in sections:
            raise ValueError("Duplicate PF2 section")
        if kind == b"DATA":
            if size != 0xffffffff:
                raise ValueError("PF2 DATA must extend to EOF")
            sections[kind] = (pos, raw[pos:])
            pos = len(raw)
            break
        if pos + size > len(raw):
            raise ValueError("Truncated PF2 section")
        sections[kind] = (pos, raw[pos:pos + size])
        pos += size
    if pos != len(raw) or sections[b"FILE"][1] != b"PFF2":
        raise ValueError("Invalid PF2 file")
    name = sections[b"NAME"][1].rstrip(b"\0").decode("ascii")
    index = sections[b"CHIX"][1]
    if not index or len(index) % 9:
        raise ValueError("Invalid PF2 character index")
    codes = set()
    for start in range(0, len(index), 9):
        code, flags, offset = struct.unpack_from(">IBI", index, start)
        if code in codes or flags or not sections[b"DATA"][0] <= offset < len(raw) - 9:
            raise ValueError("Invalid PF2 glyph index entry")
        codes.add(code)
        width, height = struct.unpack_from(">HH", raw, offset)
        if offset + 10 + (width * height + 7) // 8 > len(raw):
            raise ValueError("Truncated PF2 glyph bitmap")
    if not set(range(32, 127)) <= codes or not set(range(0x2190, 0x2194)) <= codes:
        raise ValueError("Required menu characters missing")
    return name, len(codes)


class InstalledResources(unittest.TestCase):
    @property
    def theme(self):
        return PACKAGE / "share" / "grub" / "themes" / "breeze"

    def test_exact_inventory_and_sha256(self):
        actual = {p.relative_to(PACKAGE).as_posix() for p in PACKAGE.rglob("*")
                  if p.is_file() and p.name not in ("conaninfo.txt", "conanmanifest.txt")}
        self.assertEqual(actual, set(EXPECTED), "Installed package inventory differs from upstream contract")
        for name, entry in EXPECTED.items():
            with self.subTest(file=name):
                raw = (PACKAGE / name).read_bytes()
                self.assertEqual(len(raw), entry["size"])
                self.assertEqual(hashlib.sha256(raw).hexdigest(), entry["sha256"])

    def test_png_decoding(self):
        files = sorted(self.theme.glob("*.png"))
        self.assertEqual(len(files), 12)
        for path in files:
            with self.subTest(file=path.name):
                width, height = png_info(path.read_bytes())
                self.assertGreater(width * height, 0)

    def test_pf2_fonts(self):
        fonts = {pf2_info(path.read_bytes())[0] for path in self.theme.glob("*.pf2")}
        self.assertEqual(fonts, {"Unifont Regular 14", "Unifont Regular 16", "Unifont Bold 16"})

    def test_theme_references_resolve(self):
        theme = (self.theme / "theme.txt").read_text(encoding="utf-8")
        fonts = {pf2_info(path.read_bytes())[0] for path in self.theme.glob("*.pf2")}
        references = re.findall(r'(?:[\w-]*font)\s*[:=]\s*"([^"]+)"', theme)
        self.assertTrue(references)
        self.assertTrue(set(references) <= fonts)
        patterns = re.findall(r'\w+_style\s*=\s*"([^"]+)"', theme)
        self.assertEqual(len(patterns), 4)
        for pattern in patterns:
            self.assertNotIn("/", pattern)
            self.assertTrue(list(self.theme.glob(pattern)), pattern)
        for part in ("c", "n", "s", "e", "w", "ne", "nw", "se", "sw"):
            self.assertTrue((self.theme / f"roundedsquare_{part}.png").is_file())
        self.assertIn('+ boot_menu {', theme)
        self.assertIn('id = "__timeout__"', theme)

    def test_svg_source(self):
        document = ET.parse(self.theme / "roundedsquare.svg")
        self.assertEqual(document.getroot().tag, "{http://www.w3.org/2000/svg}svg")

    def test_license_metadata(self):
        licenses = PACKAGE / "licenses"
        self.assertEqual(len(list(licenses.glob("*.txt"))), 7)
        self.assertIn("CC0-1.0", (licenses / "REUSE.toml").read_text(encoding="utf-8"))
        for font in self.theme.glob("*.pf2"):
            self.assertIn("Font-exception-2.0", Path(str(font) + ".license").read_text())

    def test_conan_discovery(self):
        exported = os.environ.get("BREEZE_GRUB_THEME_DIR")
        self.assertIsNotNone(exported, "Conan runtime resource location is missing")
        self.assertEqual(Path(exported).resolve(), self.theme.resolve())
        self.assertTrue((Path(exported) / "theme.txt").is_file())


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("package", type=Path)
    args = parser.parse_args()
    PACKAGE = args.package.resolve()
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(InstalledResources))
    raise SystemExit(0 if result.wasSuccessful() else 1)
