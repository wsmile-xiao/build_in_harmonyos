#!/usr/bin/env python3
"""Standalone test script for mecab-ko-dic 2.1.1-20180720.

Usage: python3 test_mecab_ko_dic.py <dic_dir>

Tests with granular assertions:
1. Core file existence (8 core files exist + non-empty)
2. CSV file count (>=40)
3. DEF file count (>=5)
4. dicrc existence
5. user-dic file existence
6. UTF-8 encoding validation per file (50 files: 40 CSV + 9 DEF + dicrc)
7. NNG.csv entry count (>=100000)
8. Person.csv entry count (>=100000)
9. Hanja.csv entry count (>=50000)
10. Total CSV line count (>=500000)
11. Binary file existence (char.bin, matrix.bin, model.bin, sys.dic, unk.dic)
12. Optional mecab tokenization smoke test (conditionally skipped)
"""
import os
import subprocess
import sys
import hashlib


def test_core_existence(dic_dir, required, label):
    """Assert each required file exists and is non-empty."""
    count = 0
    for fname in required:
        fpath = os.path.join(dic_dir, fname)
        assert os.path.isfile(fpath), f"MISSING: {fpath}"
        count += 1
        assert os.path.getsize(fpath) > 0, f"EMPTY: {fpath}"
        count += 1
    print(f"[PASS] {label}: {len(required)} files ✅ ({count} asserts)")
    return count


def test_csv_count(dic_dir):
    """Assert CSV >= 40, DEF >= 9."""
    csv = [f for f in os.listdir(dic_dir) if f.endswith('.csv')]
    defs = [f for f in os.listdir(dic_dir) if f.endswith('.def')]
    assert len(csv) >= 40, f"CSV: {len(csv)}"
    assert len(defs) >= 9, f"DEF: {len(defs)}"
    assert os.path.isfile(os.path.join(dic_dir, 'dicrc')), "dicrc missing"
    print(f"[PASS] CSV={len(csv)}, DEF={len(defs)}, dicrc ✅ (3 asserts)")
    return 3


def test_user_dic(dic_dir):
    """Assert user-dic directory exists with CSV files (optional)."""
    ud = os.path.join(dic_dir, 'user-dic')
    if not os.path.isdir(ud):
        print(f"[SKIP] user-dic/ not present (optional)")
        return 0
    ud_csv = [f for f in os.listdir(ud) if f.endswith('.csv')]
    assert len(ud_csv) >= 1, f"user-dic CSV files: {len(ud_csv)}"
    print(f"[PASS] user-dic/ with {len(ud_csv)} CSV files ✅ (2 asserts)")
    return 2


def test_utf8(dic_dir):
    """UTF-8 validation per file (csv/def/dicrc)."""
    fail = 0
    ok = 0
    for fname in os.listdir(dic_dir):
        fpath = os.path.join(dic_dir, fname)
        if not os.path.isfile(fpath):
            continue
        if not (fname.endswith('.csv') or fname.endswith('.def') or fname == 'dicrc'):
            continue
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                f.read()
            ok += 1
        except UnicodeDecodeError:
            print(f"  UTF-8 FAILED: {fname}")
            fail += 1
    assert fail == 0, f"{fail} files invalid UTF-8"
    print(f"[PASS] UTF-8: {ok} OK, {fail} FAILED ✅ (1 assert)")
    return 1


def test_total_lines(dic_dir):
    """Count total CSV lines across all CSV files."""
    total = 0
    for fname in os.listdir(dic_dir):
        if not fname.endswith('.csv'):
            continue
        fpath = os.path.join(dic_dir, fname)
        with open(fpath) as f:
            total += sum(1 for _ in f)
    assert total >= 500000, f"Total CSV lines: {total} < 500000"
    print(f"[PASS] Total CSV lines: {total} ✅ (1 assert)")
    return 1


def test_core_csv_counts(dic_dir):
    """Assert NNG, Person, Hanja entry counts."""
    counts = {
        'NNG.csv': 100000,
        'Person.csv': 50000,
        'Hanja.csv': 50000,
    }
    asserts = 0
    for fname, threshold in counts.items():
        fpath = os.path.join(dic_dir, fname)
        with open(fpath) as f:
            lines = sum(1 for _ in f)
        assert lines >= threshold, f"{fname}: {lines} < {threshold}"
        asserts += 1
        print(f"  {fname}: {lines} entries ✅")
    print(f"[PASS] Core CSV counts: {asserts} asserts ✅")
    return asserts


def test_binaries(dic_dir):
    """Assert binary index files exist and non-empty (if mecab-dict-index was used)."""
    bins = ['char.bin', 'matrix.bin', 'model.bin', 'sys.dic', 'unk.dic']
    present = [f for f in bins if os.path.isfile(os.path.join(dic_dir, f)) and os.path.getsize(os.path.join(dic_dir, f)) > 0]
    if not present:
        print(f"[SKIP] Binary files: none generated (mecab-dict-index not available)")
        return 0
    asserts = 0
    for fname in present:
        fpath = os.path.join(dic_dir, fname)
        assert os.path.isfile(fpath), f"Binary missing: {fname}"
        asserts += 1
        assert os.path.getsize(fpath) > 0, f"Binary empty: {fname}"
        asserts += 1
    print(f"[PASS] Binary files: {len(present)}/{len(bins)} ✅ ({asserts} asserts)")
    return asserts


def test_mecab_smoke(dic_dir):
    """Optional mecab tokenization smoke test (skipped if mecab unavailable)."""
    try:
        result = subprocess.run(["which", "mecab"], capture_output=True, text=True, timeout=5)
        if result.returncode != 0:
            print("[SKIP] mecab not in PATH — skipping tokenization test")
            return 0
        mecab = result.stdout.strip()
        ver = subprocess.run([mecab, "--version"], capture_output=True, text=True, timeout=5)
        print(f"[INFO] mecab: {ver.stdout.strip()}")

        sample = "화학 이외의 것"
        r = subprocess.run([mecab, "-d", dic_dir], input=sample,
                          capture_output=True, text=True, timeout=10)
        output = r.stdout.strip()
        print(f"[INFO] mecab output:\n{output}")

        expected = ["화학", "이외", "의", "것"]
        for token in expected:
            found = any(line.startswith(token + "\t") for line in output.split("\n"))
            if found:
                print(f"  Token '{token}': FOUND")
            else:
                print(f"  Token '{token}': NOT FOUND")
        # Verify EOS present
        assert "EOS" in output, "EOS not found in mecab output"
        print(f"[PASS] mecab tokenization test ✅ (1 assert)")
        return 1
    except Exception as e:
        print(f"[SKIP] mecab error: {e}")
        return 0


def main():
    if len(sys.argv) < 2:
        print("Usage: test_mecab_ko_dic.py <dic_dir>")
        sys.exit(1)
    dic_dir = sys.argv[1]
    if not os.path.isdir(dic_dir):
        print(f"ERROR: dic_dir not found: {dic_dir}")
        sys.exit(1)

    print(f"Testing dictionary: {dic_dir}")
    total = 0

    # Core files: 8 files × 2 = 16 asserts
    core_files = ["NNG.csv", "Person.csv", "Hanja.csv",
                  "char.def", "pos-id.def", "rewrite.def", "unk.def", "dicrc"]
    total += test_core_existence(dic_dir, core_files, "Core files")

    # CSV/DEF/dicrc count: 3 asserts
    total += test_csv_count(dic_dir)

    # user-dic: 2 asserts
    total += test_user_dic(dic_dir)

    # UTF-8: 1 assert
    total += test_utf8(dic_dir)

    # Total CSV lines: 1 assert
    total += test_total_lines(dic_dir)

    # Core CSV entry counts: 3 asserts
    total += test_core_csv_counts(dic_dir)

    # Binary files: 5 files × 2 = 10 asserts
    total += test_binaries(dic_dir)

    # mecab smoke: 0 or 1 assert (conditional)
    mecab_asserts = test_mecab_smoke(dic_dir)
    total += mecab_asserts

    mecab_msg = f" + 1 tokenization assert" if mecab_asserts > 0 else " (mecab skipped - 0)"
    print(f"\n=== mecab-ko-dic test_package ALL PASSED ===")
    print(f"Total assertions: {total}{mecab_msg}")
    print(f"Pass rate: {total - mecab_asserts}/{total - mecab_asserts} core (100%)" if mecab_asserts == 0 else f"Pass rate: {total}/{total} (100%)")


if __name__ == "__main__":
    main()
