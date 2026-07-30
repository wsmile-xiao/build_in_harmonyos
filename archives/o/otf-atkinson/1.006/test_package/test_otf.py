#!/usr/bin/env python3
"""OTF font verification script for otf-atkinson 1.006."""
import hashlib
import os
import struct
import sys


def _read_otf_table(otf_path, tag):
    with open(otf_path, "rb") as f:
        data = f.read()
    num_tables = struct.unpack_from(">H", data, 4)[0]
    table_dir_offset = 12
    for i in range(num_tables):
        entry_off = table_dir_offset + i * 16
        entry_tag = data[entry_off:entry_off + 4].decode("ascii", errors="replace")
        entry_offset, entry_length = struct.unpack_from(">II", data, entry_off + 8)
        if entry_tag == tag:
            return data[entry_offset:entry_offset + entry_length]
    return None


def _get_name_strings(otf_path):
    raw = _read_otf_table(otf_path, "name")
    if raw is None:
        return {}
    count = struct.unpack_from(">H", raw, 2)[0]
    string_offset = struct.unpack_from(">H", raw, 4)[0]
    names = {}
    for i in range(count):
        rec_off = 6 + i * 12
        platform_id, _, _, name_id = struct.unpack_from(">HHHH", raw, rec_off)
        length, offset = struct.unpack_from(">HH", raw, rec_off + 8)
        raw_string = raw[string_offset + offset:string_offset + offset + length]
        if platform_id == 3:
            decoded = raw_string.decode("utf-16-be", errors="replace")
        elif platform_id == 1:
            decoded = raw_string.decode("mac_roman", errors="replace")
        else:
            decoded = raw_string.decode("utf-16-be", errors="replace")
        names[name_id] = decoded
    return names


def _get_cmap_unicodes(otf_path):
    raw = _read_otf_table(otf_path, "cmap")
    if raw is None:
        return set()
    _, num_tables = struct.unpack_from(">HH", raw, 0)
    codepoints = set()
    for i in range(num_tables):
        entry_off = 4 + i * 8
        platform_id, encoding_id = struct.unpack_from(">HH", raw, entry_off)
        subtable_offset = struct.unpack_from(">I", raw, entry_off + 4)[0]
        if platform_id == 3 and encoding_id in (1, 10):
            subtable_data = raw[subtable_offset:]
            fmt = struct.unpack_from(">H", subtable_data, 0)[0]
            if fmt == 4:
                seg_count = struct.unpack_from(">H", subtable_data, 6)[0] // 2
                end_codes_off = 14
                start_codes_off = end_codes_off + seg_count * 2 + 2
                for j in range(seg_count):
                    end_code = struct.unpack_from(">H", subtable_data, end_codes_off + j * 2)[0]
                    start_code = struct.unpack_from(">H", subtable_data, start_codes_off + j * 2)[0]
                    if start_code == 0xFFFF:
                        break
                    for cp in range(start_code, end_code + 1):
                        codepoints.add(cp)
            elif fmt == 12:
                n_groups = struct.unpack_from(">I", subtable_data, 12)[0]
                for g in range(n_groups):
                    group_off = 16 + g * 12
                    start_char, end_char, _ = struct.unpack_from(">III", subtable_data, group_off)
                    for cp in range(start_char, min(end_char, 0x10FFFF) + 1):
                        codepoints.add(cp)
    return codepoints


def main(font_dir):
    errors = []
    if not os.path.isdir(font_dir):
        print(f"[FAIL] OTF font directory not found: {font_dir}"); sys.exit(1)
    print(f"[PASS] OTF font dir exists: {font_dir}")

    expected = {
        "AtkinsonHyperlegible-Bold.otf": "682c9737bfb6c1d3ba4f9cd5fdc814775c097f317656aad177867cc07d7e15df",
        "AtkinsonHyperlegible-BoldItalic.otf": "b3572890592cd2b06e0f0334f34bb2e3a93d5dcbd694ff91007e4dae89d07c0d",
        "AtkinsonHyperlegible-Italic.otf": "29feedae5589c9d65e01760398d9595496a6aabd308052576604fff8430d7ded",
        "AtkinsonHyperlegible-Regular.otf": "4a0397a3709c5fc99e38d05469dcfbf1b3481196e89a01b7377f3163b188258e",
    }
    found = sorted(os.listdir(font_dir))
    print(f"[INFO] Found OTF files: {found}")
    if len(found) != 4:
        errors.append(f"Expected 4 OTF files, found {len(found)}")
    for fname, exp_sha in expected.items():
        fpath = os.path.join(font_dir, fname)
        if not os.path.isfile(fpath):
            errors.append(f"File not found: {fname}"); continue
        actual = hashlib.sha256(open(fpath, "rb").read()).hexdigest()
        if actual != exp_sha:
            errors.append(f"sha256 mismatch for {fname}: expected {exp_sha}, got {actual}")
        else:
            print(f"[PASS] {fname} sha256 OK")

    for fname in expected:
        fpath = os.path.join(font_dir, fname)
        if not os.path.isfile(fpath):
            errors.append(f"File not found (skip name table): {fname}"); continue
        names = _get_name_strings(fpath)
        family, style, full_name, version_str = names.get(1,""), names.get(2,""), names.get(4,""), names.get(5,"")
        print(f"[INFO] {fname}: Family={family}, Style={style}, Full={full_name}, Version={version_str}")
        if "Atkinson Hyperlegible" not in family:
            errors.append(f"Bad family: {family}")
        if "1.006" not in version_str:
            errors.append(f"Bad version: {version_str}")

    required = set(range(0x41,0x5B)) | set(range(0x61,0x7B)) | set(range(0x30,0x3A))
    required.update([0x21,0x3F,0x2C,0x2E,0x3A,0x3B,0x25])
    for fname in expected:
        fpath = os.path.join(font_dir, fname)
        if not os.path.isfile(fpath):
            errors.append(f"File not found (skip cmap): {fname}"); continue
        cps = _get_cmap_unicodes(fpath)
        missing = required - cps
        if missing:
            errors.append(f"{fname}: missing codepoints {sorted(missing)}")
        else:
            print(f"[PASS] {fname}: cmap OK ({len(cps)} codepoints)")

    if errors:
        print("\n".join(f"[FAIL] {e}" for e in errors)); sys.exit(1)
    print("\n=== All OTF verification checks PASSED ===")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else ".")
