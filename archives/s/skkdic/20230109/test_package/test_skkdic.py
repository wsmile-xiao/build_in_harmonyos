#!/usr/bin/env python3
"""Standalone test script for skkdic 20230109.

Usage: python3 test_skkdic.py <datadir>

Tests with granular assertions:
1. Core file existence (20 core dictionaries exist + non-empty)
2. SKK dictionary format validation (parsing reading/candidate/annotation format)
3. Minimum entry counts for major dictionaries
4. Total dictionary file count (>= 30)
5. Provenance documents (ChangeLog, unicode-license.txt)
"""
import os
import sys


def test_core_existence(datadir, required):
    """Test that all required dictionary files exist and are non-empty."""
    count = 0
    for fname in required:
        fpath = os.path.join(datadir, fname)
        assert os.path.isfile(fpath), f"MISSING: {fpath}"
        count += 1
        assert os.path.getsize(fpath) > 0, f"EMPTY: {fpath}"
        count += 1
    print(f"[PASS] core files: {len(required)} files (OK) ({count} asserts)")
    return count


def scan_dictionary(datadir, name):
    """Scan one dictionary and confirm it really looks like SKK dictionary data.
    Returns the number of well-formed entries found.
    Raises AssertionError on failure."""
    path = os.path.join(datadir, name)
    entries = 0
    lines = 0
    malformed = 0

    with open(path, 'r', encoding='utf-8', errors='replace') as f:
        for line in f:
            line = line.rstrip('\n\r')
            if not line:
                continue
            # Comment lines start with ';' and carry no entry
            if line[0] == ';':
                continue
            lines += 1
            # A dictionary entry must separate reading and candidates by a space
            sep = line.find(' ')
            if sep == -1 or sep == 0:
                malformed += 1
            else:
                entries += 1

    assert lines > 0, f"{name} has no content"
    assert entries > 0, f"{name} has no well-formed SKK entries"
    # Allow a few odd lines, but the bulk of a real dictionary must parse
    assert malformed <= lines // 20, f"{name} mostly malformed ({malformed}/{lines})"
    return entries


def test_skk_format(datadir):
    """Test SKK dictionary format parsing for major dictionaries."""
    count = 0

    # SKK-JISYO.L - main dictionary
    entries = scan_dictionary(datadir, "SKK-JISYO.L")
    assert entries > 1000, f"SKK-JISYO.L has too few entries: {entries}"
    print(f"[PASS] SKK-JISYO.L: {entries} entries (OK) (4 asserts)")
    count += 4

    # SKK-JISYO.zipcode - postal code dictionary
    entries = scan_dictionary(datadir, "SKK-JISYO.zipcode")
    assert entries > 0, "SKK-JISYO.zipcode has no entries"
    print(f"[PASS] SKK-JISYO.zipcode: {entries} entries (OK) (4 asserts)")
    count += 4

    # SKK-JISYO.assoc - derived dictionary
    entries = scan_dictionary(datadir, "SKK-JISYO.assoc")
    assert entries > 0, "SKK-JISYO.assoc has no entries"
    print(f"[PASS] SKK-JISYO.assoc: {entries} entries (OK) (4 asserts)")
    count += 4

    return count


def test_total_count(datadir):
    """Test total dictionary file count."""
    d = os.listdir(datadir)
    ndict = sum(1 for f in d if f.startswith("SKK-JISYO."))
    assert ndict >= 30, f"Too few dictionary files: {ndict}"
    print(f"[PASS] dictionary files installed: {ndict} (OK) (1 assert)")
    return 1


def test_provenance(datadir):
    """Test provenance documents."""
    count = 0
    for fname in ("ChangeLog", "unicode-license.txt"):
        fpath = os.path.join(datadir, fname)
        assert os.path.isfile(fpath), f"MISSING: {fname}"
        assert os.path.getsize(fpath) > 0, f"EMPTY: {fname}"
        count += 2
        print(f"[PASS] {fname} (OK) (2 asserts)")
    return count


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 test_skkdic.py <datadir>")
        sys.exit(2)
    datadir = sys.argv[1]
    assert os.path.isdir(datadir), f"datadir not found: {datadir}"

    # 20 core dictionaries that must exist
    required_dicts = [
        "SKK-JISYO.L",
        "SKK-JISYO.L.unannotated",
        "SKK-JISYO.ML",
        "SKK-JISYO.M",
        "SKK-JISYO.S",
        "SKK-JISYO.JIS2",
        "SKK-JISYO.JIS3_4",
        "SKK-JISYO.JIS2004",
        "SKK-JISYO.edict",
        "SKK-JISYO.edict2",
        "SKK-JISYO.assoc",
        "SKK-JISYO.geo",
        "SKK-JISYO.jinmei",
        "SKK-JISYO.law",
        "SKK-JISYO.lisp",
        "SKK-JISYO.mazegaki",
        "SKK-JISYO.okinawa",
        "SKK-JISYO.propernoun",
        "SKK-JISYO.station",
        "SKK-JISYO.zipcode",
    ]

    total_asserts = 1  # assert os.path.isdir above
    total_asserts += test_core_existence(datadir, required_dicts)
    total_asserts += test_skk_format(datadir)
    total_asserts += test_total_count(datadir)
    total_asserts += test_provenance(datadir)

    print(f"\n=== skkdic consumer test PASSED -- {total_asserts} assertions ===")
    sys.exit(0)


if __name__ == '__main__':
    main()
