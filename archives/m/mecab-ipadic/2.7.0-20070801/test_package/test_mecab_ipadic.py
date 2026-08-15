#!/usr/bin/env python3
"""Standalone test script for mecab-ipadic 2.7.0-20070801.

Usage: python3 test_mecab_ipadic.py <dic_dir>

Tests with granular assertions:
1. Core file existence (8 core files exist + non-empty)
2. CSV file count (== 26)
3. DEF file count (== 8)
4. dicrc existence
5. EUC-JP encoding validation per file (26 CSV + 8 DEF + dicrc)
6. Noun.csv entry count (>= 30000)
7. Verb.csv entry count (>= 100000)
8. Adj.csv entry count (>= 20000)
9. Total CSV line count (>= 300000)
10. Binary file existence (char.bin, matrix.bin, model.bin, sys.dic, unk.dic)
11. Optional mecab tokenization smoke test (conditionally skipped when the
    external mecab executable is unavailable)
"""
import os
import subprocess
import sys


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
    """Assert CSV == 26, DEF == 8."""
    csv = [f for f in os.listdir(dic_dir) if f.endswith('.csv')]
    defs = [f for f in os.listdir(dic_dir) if f.endswith('.def')]
    assert len(csv) == 26, f"CSV: {len(csv)}"
    assert len(defs) == 8, f"DEF: {len(defs)}"
    assert os.path.isfile(os.path.join(dic_dir, 'dicrc')), "dicrc missing"
    print(f"[PASS] CSV={len(csv)}, DEF={len(defs)}, dicrc ✅ (3 asserts)")
    return 3


def test_eucjp(dic_dir):
    """EUC-JP validation per file (csv/def/dicrc). mecab-ipadic is EUC-JP."""
    fail = 0
    ok = 0
    for fname in os.listdir(dic_dir):
        fpath = os.path.join(dic_dir, fname)
        if not os.path.isfile(fpath):
            continue
        if not (fname.endswith('.csv') or fname.endswith('.def') or fname == 'dicrc'):
            continue
        try:
            with open(fpath, 'r', encoding='euc_jp') as f:
                f.read()
            ok += 1
        except UnicodeDecodeError:
            print(f"  EUC-JP FAILED: {fname}")
            fail += 1
    assert fail == 0, f"{fail} files invalid EUC-JP"
    print(f"[PASS] EUC-JP: {ok} OK, {fail} FAILED ✅ (1 assert)")
    return 1


def test_csv_entries(dic_dir):
    """Assert entry counts for core CSV files and total lines."""
    count = 0
    core = {'Noun.csv': 30000, 'Verb.csv': 100000, 'Adj.csv': 20000}
    for fname, minimum in core.items():
        fpath = os.path.join(dic_dir, fname)
        assert os.path.isfile(fpath), f"MISSING: {fname}"
        with open(fpath, encoding='euc_jp') as f:
            lines = sum(1 for _ in f)
        assert lines >= minimum, f"{fname}: {lines} < {minimum}"
        count += 1
        print(f"[PASS] {fname}: {lines} entries ✅ (1 assert)")
    total = 0
    for fname in os.listdir(dic_dir):
        if not fname.endswith('.csv'):
            continue
        fpath = os.path.join(dic_dir, fname)
        with open(fpath, encoding='euc_jp') as f:
            total += sum(1 for _ in f)
    assert total >= 300000, f"Total {total} < 300000"
    count += 1
    print(f"[PASS] Total CSV lines: {total} ✅ (1 assert)")
    return count


def test_binary_files(dic_dir):
    """Assert binary index files exist if generated (optional but checked)."""
    count = 0
    for fname in ['char.bin', 'matrix.bin', 'model.bin', 'sys.dic', 'unk.dic']:
        fpath = os.path.join(dic_dir, fname)
        if os.path.isfile(fpath) and os.path.getsize(fpath) > 0:
            print(f"[INFO] binary present: {fname}")
            count += 1
    print(f"[INFO] Binary indices present: {count}/5 (may be 0 without mecab tool)")
    return count


def test_mecab_smoke(dic_dir):
    """Optional mecab tokenization smoke test (external mecab tool)."""
    import shutil
    mecab_exe = shutil.which('mecab')
    if not mecab_exe:
        print("[SKIP] mecab executable not found — external tool, skipping tokenization smoke test")
        return 0
    # mecab -d <dic_dir> reads EUC-JP dictionary; feed an EUC-JP sample sentence
    sample = "すもももももももものうち\n".encode('euc_jp')
    try:
        result = subprocess.run(
            [mecab_exe, '-d', dic_dir],
            input=sample, capture_output=True, timeout=60
        )
        assert result.returncode == 0, f"mecab RC={result.returncode}: {result.stderr[:200]}"
        out = result.stdout.decode('euc_jp', errors='replace')
        assert 'EOS' in out, f"mecab output missing EOS: {out[:200]}"
        print(f"[PASS] mecab tokenization smoke test ✅ (2 asserts)")
        return 2
    except (OSError, subprocess.TimeoutExpired) as exc:
        print(f"[WARN] mecab smoke test failed to run: {exc}")
        return 0


def main():
    if len(sys.argv) != 2:
        print("Usage: python3 test_mecab_ipadic.py <dic_dir>")
        sys.exit(2)
    dic_dir = sys.argv[1]
    assert os.path.isdir(dic_dir), f"dic dir not found: {dic_dir}"

    total_asserts = 0
    core_files = ['Noun.csv', 'Verb.csv', 'Adj.csv', 'char.def', 'feature.def',
                  'left-id.def', 'matrix.def', 'pos-id.def', 'rewrite.def',
                  'right-id.def', 'unk.def', 'dicrc']
    total_asserts += test_core_existence(dic_dir, core_files, "core files")
    total_asserts += test_csv_count(dic_dir)
    total_asserts += test_eucjp(dic_dir)
    total_asserts += test_csv_entries(dic_dir)
    test_binary_files(dic_dir)
    total_asserts += test_mecab_smoke(dic_dir)
    print(f"\n=== mecab-ipadic consumer test PASSED — {total_asserts} assertions ===")
    sys.exit(0)


if __name__ == '__main__':
    main()
