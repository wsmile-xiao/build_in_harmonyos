#!/usr/bin/env python3
"""Consumer-side validation for the Campania font resource package."""
import os
import struct
import sys
import zlib


FONT_MAGIC = {
    ".otf": (b"OTTO", b"\x00\x01\x00\x00"),
    ".ttf": (b"\x00\x01\x00\x00", b"true"),
    ".woff": (b"wOFF",),
}
EXPECTED_FONTS = {"Campania.otf", "Campania.ttf", "Campania.woff"}
EXPECTED_FEATURE_FILES = {
    "Campania.fea",
    "CampaniaCLASSES.fea",
    "CampaniaGSUB.fea",
    "CampaniaGPOS.fea",
}
REQUIRED_TABLES = {
    "head",
    "hhea",
    "maxp",
    "name",
    "cmap",
    "hmtx",
    "GDEF",
    "GPOS",
    "GSUB",
}


class ValidationError(Exception):
    pass


def fail(message):
    print(f"[fail] {message}")
    raise SystemExit(1)


def u16(data, offset):
    return struct.unpack_from(">H", data, offset)[0]


def u32(data, offset):
    return struct.unpack_from(">I", data, offset)[0]


def sfnt_tables(data):
    if len(data) < 12:
        raise ValidationError("SFNT file is shorter than its header")
    version = data[:4]
    if version not in FONT_MAGIC[".otf"] + FONT_MAGIC[".ttf"]:
        raise ValidationError(f"unexpected SFNT version: {version!r}")
    count = u16(data, 4)
    directory_end = 12 + count * 16
    if directory_end > len(data):
        raise ValidationError("SFNT table directory exceeds file size")
    tables = {}
    for index in range(count):
        offset = 12 + index * 16
        tag = data[offset:offset + 4].decode("ascii", "replace")
        table_offset = u32(data, offset + 8)
        table_length = u32(data, offset + 12)
        if table_offset + table_length > len(data):
            raise ValidationError(f"{tag} table exceeds file size")
        tables[tag] = data[table_offset:table_offset + table_length]
    return version, tables


def woff_tables(data):
    if len(data) < 44 or data[:4] != b"wOFF":
        raise ValidationError("invalid WOFF header")
    flavor = data[4:8]
    if flavor not in FONT_MAGIC[".otf"] + FONT_MAGIC[".ttf"]:
        raise ValidationError(f"unexpected WOFF flavor: {flavor!r}")
    count = u16(data, 12)
    total_length = u32(data, 8)
    if total_length != len(data):
        raise ValidationError(f"WOFF totalLength {total_length} != file size {len(data)}")
    directory_end = 44 + count * 20
    if directory_end > len(data):
        raise ValidationError("WOFF table directory exceeds file size")
    tables = {}
    for index in range(count):
        offset = 44 + index * 20
        tag = data[offset:offset + 4].decode("ascii", "replace")
        table_offset = u32(data, offset + 4)
        compressed_length = u32(data, offset + 8)
        original_length = u32(data, offset + 12)
        if table_offset + compressed_length > len(data):
            raise ValidationError(f"WOFF {tag} data exceeds file size")
        raw = data[table_offset:table_offset + compressed_length]
        table = zlib.decompress(raw) if compressed_length < original_length else raw
        if len(table) != original_length:
            raise ValidationError(f"WOFF {tag} decompressed length mismatch")
        tables[tag] = table
    return flavor, tables


def parse_font(path):
    with open(path, "rb") as stream:
        data = stream.read()
    suffix = os.path.splitext(path)[1].lower()
    if suffix == ".woff":
        flavor, tables = woff_tables(data)
    else:
        flavor, tables = sfnt_tables(data)
    return data, flavor, tables


def cmap_codepoints(table):
    if len(table) < 4:
        raise ValidationError("cmap table is truncated")
    records = u16(table, 2)
    chosen = None
    for index in range(records):
        offset = 4 + index * 8
        if offset + 8 > len(table):
            raise ValidationError("cmap encoding records are truncated")
        subtable_offset = u32(table, offset + 4)
        if subtable_offset + 2 > len(table):
            raise ValidationError("cmap subtable is out of bounds")
        fmt = u16(table, subtable_offset)
        platform = u16(table, offset)
        encoding = u16(table, offset + 2)
        priority = (fmt == 12, platform == 3, encoding in (1, 10))
        if fmt in (4, 12) and (chosen is None or priority > chosen[0]):
            chosen = (priority, subtable_offset, fmt)
    if chosen is None:
        raise ValidationError("cmap has no format 4 or format 12 Unicode subtable")
    _, offset, fmt = chosen
    if fmt == 12:
        groups = u32(table, offset + 12)
        codepoints = set()
        for index in range(groups):
            start = offset + 16 + index * 12
            if start + 12 > len(table):
                raise ValidationError("cmap format 12 groups are truncated")
            first, last = u32(table, start), u32(table, start + 4)
            if last < first or last - first > 0x10000:
                raise ValidationError("invalid cmap format 12 range")
            codepoints.update(range(first, last + 1))
        return codepoints
    length = u16(table, offset + 2)
    end = offset + length
    if end > len(table) or length < 16:
        raise ValidationError("cmap format 4 is truncated")
    segments = u16(table, offset + 6) // 2
    if offset + 16 + segments * 2 > end:
        raise ValidationError("cmap format 4 segments are truncated")
    codepoints = set()
    end_codes = [u16(table, offset + 14 + i * 2) for i in range(segments)]
    start_base = offset + 16 + segments * 2
    starts = [u16(table, start_base + i * 2) for i in range(segments)]
    for start_code, end_code in zip(starts, end_codes):
        if end_code < start_code:
            raise ValidationError("invalid cmap format 4 range")
        if end_code - start_code <= 0x10000:
            codepoints.update(range(start_code, end_code + 1))
    return codepoints


def check_font(name, path):
    data, flavor, tables = parse_font(path)
    suffix = os.path.splitext(path)[1].lower()
    if data[:4] not in FONT_MAGIC[suffix]:
        raise ValidationError(f"invalid {suffix} signature: {data[:4]!r}")
    missing = REQUIRED_TABLES - set(tables)
    if missing:
        raise ValidationError(f"missing required OpenType tables: {sorted(missing)}")
    outline = "CFF " if suffix == ".otf" else "glyf"
    if suffix != ".woff" and outline not in tables:
        raise ValidationError(f"missing {outline} outline table")
    if suffix == ".ttf" and "loca" not in tables:
        raise ValidationError("missing loca table for TrueType font")
    if suffix == ".otf" and "CFF " not in tables:
        raise ValidationError("missing CFF table for OpenType font")
    codepoints = cmap_codepoints(tables["cmap"])
    required_chars = {ord(char) for char in "b#h01234679o^-=\\"}
    if not required_chars.issubset(codepoints):
        missing_chars = sorted(required_chars - codepoints)
        raise ValidationError(f"cmap lacks Campania input characters: {missing_chars}")
    for table_name in ("GSUB", "GPOS", "GDEF"):
        if len(tables[table_name]) < 10:
            raise ValidationError(f"{table_name} table is unexpectedly short")
    if b"Campania" not in tables["name"]:
        raise ValidationError("name table does not contain Campania family name")
    print(f"[ok] {name}: {len(tables)} tables, {len(codepoints)} mapped codepoints")
    return tables, codepoints


def check_feature_sources(source_dir):
    found = {name for name in os.listdir(source_dir) if name.endswith(".fea")}
    if found != EXPECTED_FEATURE_FILES:
        raise ValidationError(f"feature file set mismatch: {sorted(found)}")
    main = open(os.path.join(source_dir, "Campania.fea"), encoding="utf-8").read()
    for include_name in ("CampaniaCLASSES.fea", "CampaniaGSUB.fea", "CampaniaGPOS.fea"):
        if f"include({include_name});" not in main:
            raise ValidationError(f"Campania.fea does not include {include_name}")
    gsub = open(os.path.join(source_dir, "CampaniaGSUB.fea"), encoding="utf-8").read()
    gpos = open(os.path.join(source_dir, "CampaniaGPOS.fea"), encoding="utf-8").read()
    for feature in ("feature liga", "feature calt"):
        if feature not in gsub:
            raise ValidationError(f"GSUB source lacks {feature}")
    if "feature kern" not in gpos or "lookup symbol_spacing" not in gpos:
        raise ValidationError("GPOS source lacks kern/symbol_spacing feature")
    print(f"[ok] feature sources: {len(found)} files, includes and feature declarations valid")


def main():
    font_dir = sys.argv[1] if len(sys.argv) > 1 else "fonts"
    license_dir = sys.argv[2] if len(sys.argv) > 2 else "licenses"
    source_dir = sys.argv[3] if len(sys.argv) > 3 else os.getcwd()
    if not os.path.isdir(font_dir):
        fail(f"font directory not found: {font_dir}")
    if not os.path.isdir(license_dir):
        fail(f"license directory not found: {license_dir}")
    if not os.path.isdir(source_dir):
        fail(f"source directory not found: {source_dir}")

    fonts = {name for name in os.listdir(font_dir) if name.lower().endswith((".otf", ".ttf", ".woff"))}
    if fonts != EXPECTED_FONTS:
        fail(f"expected {sorted(EXPECTED_FONTS)}, found {sorted(fonts)}")
    if len(fonts) != 3:
        fail("Campania must provide exactly three font formats")

    parsed = {}
    for name in sorted(fonts):
        path = os.path.join(font_dir, name)
        if os.path.getsize(path) == 0:
            fail(f"empty font file: {name}")
        try:
            parsed[name] = check_font(name, path)
        except (OSError, struct.error, zlib.error, ValidationError) as error:
            fail(f"{name}: {error}")

    otf_points = parsed["Campania.otf"][1]
    ttf_points = parsed["Campania.ttf"][1]
    if otf_points != ttf_points:
        fail("OTF and TTF cmap codepoint sets differ")
    print(f"[ok] OTF/TTF cmap parity: {len(otf_points)} codepoints")

    try:
        check_feature_sources(source_dir)
    except (OSError, ValidationError) as error:
        fail(str(error))

    for name in ("LICENSE", "README.md"):
        path = os.path.join(license_dir, name)
        if not os.path.isfile(path) or os.path.getsize(path) == 0:
            fail(f"missing packaged documentation: {name}")
        print(f"[ok] {name}")

    print("[ok] Campania resource, SFNT/WOFF, OpenType feature, cmap, and documentation checks passed")


if __name__ == "__main__":
    main()
