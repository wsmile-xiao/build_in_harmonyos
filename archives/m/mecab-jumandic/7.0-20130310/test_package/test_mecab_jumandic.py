#!/usr/bin/env python3
"""Standalone test script for mecab-jumandic 7.0-20130310.

Usage: python3 test_mecab_jumandic.py <dic_dir>

Tests with granular assertions:
1.  Core file existence (8 core files exist + non-empty)
2.  CSV file count (== 16), DEF file count (== 9), dicrc exists
3.  UTF-8 validation (21 files strictly clean; 4 known files carry
    upstream-inherited truncated-UTF-8 line endings — exact bad-line budget)
4.  Core CSV entry counts (ContentW/Wikipedia/Auto/Noun.koyuu/Suffix)
5.  Total CSV line count (== 751185, exact upstream figure)
6.  Binary index existence (char.bin, matrix.bin, model.bin, sys.dic, unk.dic
    — REQUIRED, generated deterministically by the recipe via tool_requires)
7.  dicrc installed next to binary indices (mecab load_dictionary_resource
    requires <dicdir>/dicrc)
"""
import os
import sys

# Upstream-inherited UTF-8 quirk budget (see recipe build()): 4 files end
# ~2937 lines with a truncated 2-byte UTF-8 sequence; Debian ships them
# unpatched and mecab-dict-index tolerates them.
EXPECTED_UTF8_QUIRKS = {'AuxV.csv': 6, 'left-id.def': 6, 'right-id.def': 6, 'model.def': 2919}


def test_core_existence(dic_dir, required):
    count = 0
    for fname in required:
        fpath = os.path.join(dic_dir, fname)
        assert os.path.isfile(fpath), f"MISSING: {fpath}"
        count += 1
        assert os.path.getsize(fpath) > 0, f"EMPTY: {fpath}"
        count += 1
    print(f"[PASS] core files: {len(required)} files ✅ ({count} asserts)")
    return count


def test_counts(dic_dir):
    csv = [f for f in os.listdir(dic_dir) if f.endswith('.csv')]
    defs = [f for f in os.listdir(dic_dir) if f.endswith('.def')]
    assert len(csv) == 16, f"CSV: {len(csv)}"
    assert len(defs) == 9, f"DEF: {len(defs)}"
    assert os.path.isfile(os.path.join(dic_dir, 'dicrc')), "dicrc missing"
    print(f"[PASS] CSV={len(csv)}, DEF={len(defs)}, dicrc ✅ (3 asserts)")
    return 3


def test_utf8(dic_dir):
    count = 0
    for fname in sorted(os.listdir(dic_dir)):
        fpath = os.path.join(dic_dir, fname)
        if not os.path.isfile(fpath):
            continue
        if not (fname.endswith('.csv') or fname.endswith('.def') or fname == 'dicrc'):
            continue
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                f.read()
            if fname in EXPECTED_UTF8_QUIRKS:
                raise AssertionError(f"{fname} expected upstream UTF-8 quirk but file is clean")
        except UnicodeDecodeError:
            expected = EXPECTED_UTF8_QUIRKS.get(fname, 0)
            bad_lines = 0
            with open(fpath, 'rb') as f:
                for raw in f:
                    try:
                        raw.decode('utf-8')
                    except UnicodeDecodeError:
                        bad_lines += 1
            assert bad_lines == expected, \
                f"{fname}: {bad_lines} bad UTF-8 lines, expected {expected} (upstream quirk budget)"
            print(f"[PASS] UTF-8 quirk as-is: {fname} ({bad_lines} truncated lines, upstream-inherited) ✅")
        count += 1
    print(f"[PASS] UTF-8 validation across {count} files ✅ ({count} asserts)")
    return count


def test_csv_entries(dic_dir):
    count = 0
    core = {'ContentW.csv': 500000, 'Wikipedia.csv': 100000, 'Auto.csv': 10000,
            'Noun.koyuu.csv': 5000, 'Suffix.csv': 1000}
    for fname, minimum in core.items():
        fpath = os.path.join(dic_dir, fname)
        assert os.path.isfile(fpath), f"MISSING: {fname}"
        with open(fpath, encoding='utf-8', errors='replace') as f:
            lines = sum(1 for _ in f)
        assert lines >= minimum, f"{fname}: {lines} < {minimum}"
        count += 1
        print(f"[PASS] {fname}: {lines} entries ✅ (1 assert)")
    total = 0
    for fname in os.listdir(dic_dir):
        if not fname.endswith('.csv'):
            continue
        fpath = os.path.join(dic_dir, fname)
        with open(fpath, encoding='utf-8', errors='replace') as f:
            total += sum(1 for _ in f)
    assert total == 751185, f"Total {total} != 751185 (upstream exact figure)"
    count += 1
    print(f"[PASS] Total CSV lines: {total} (exact upstream figure) ✅ (1 assert)")
    return count


def test_binary_indices(dic_dir):
    """Binary indices are REQUIRED — the recipe generates them
    deterministically via tool_requires('mecab/0.996')."""
    count = 0
    for fname in ['char.bin', 'matrix.bin', 'model.bin', 'sys.dic', 'unk.dic']:
        fpath = os.path.join(dic_dir, fname)
        assert os.path.isfile(fpath), f"MISSING binary index: {fname}"
        count += 1
        assert os.path.getsize(fpath) > 0, f"EMPTY binary index: {fname}"
        count += 1
        print(f"[PASS] binary index: {fname} ({os.path.getsize(fpath)} bytes) ✅ (2 asserts)")
    # dicrc must sit next to the indices (mecab loads <dicdir>/dicrc)
    assert os.path.isfile(os.path.join(dic_dir, 'dicrc')), "dicrc missing next to binary indices"
    count += 1
    print("[PASS] dicrc installed next to binary indices ✅ (1 assert)")
    return count


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 test_mecab_jumandic.py <dic_dir>")
        sys.exit(2)
    dic_dir = sys.argv[1]
    assert os.path.isdir(dic_dir), f"dic dir not found: {dic_dir}"

    core_files = ['ContentW.csv', 'Wikipedia.csv', 'Auto.csv', 'Noun.koyuu.csv',
                  'Suffix.csv', 'char.def', 'feature.def', 'left-id.def', 'matrix.def',
                  'model.def', 'pos-id.def', 'rewrite.def', 'right-id.def', 'unk.def',
                  'dicrc', 'sys.dic', 'unk.dic']
    total_asserts = 0
    total_asserts += test_core_existence(dic_dir, core_files)
    total_asserts += test_counts(dic_dir)
    total_asserts += test_utf8(dic_dir)
    total_asserts += test_csv_entries(dic_dir)
    total_asserts += test_binary_indices(dic_dir)
    print(f"\n=== mecab-jumandic consumer test PASSED — {total_asserts} assertions ===")
    sys.exit(0)


if __name__ == '__main__':
    main()
