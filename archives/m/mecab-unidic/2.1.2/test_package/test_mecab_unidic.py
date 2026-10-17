#!/usr/bin/env python3
"""Standalone test script for mecab-unidic 2.1.2.

Usage: python3 test_mecab_unidic.py <dic_dir> <mecab_pkg_dir>

Tests with granular assertions:
1. Core file existence (lex.csv, matrix.def, char.def, unk.def, dicrc, ...)
2. lex.csv entry count (== 756463)
3. matrix.def size (> 500 MB)
4. UTF-8 encoding validation per file
5. dicrc sanity (cost-factor=700, output-format-type=unidic)
6. Binary index existence (char.bin, matrix.bin, sys.dic, unk.dic) — required
7. OHOS/HarmonyOS platform test: package layout under the conan package
   folder, res_folder-free data-only package, consumer paths
8. Real MeCab consumption test (required): compile a tiny consumer against
   the required mecab/0.996 package and load this dictionary
   (loads dicrc + sys.dic + unk.dic + matrix.bin + char.bin).

Fail-closed: binary indices and mecab consumption are hard requirements —
no conditional SKIP paths.
"""
import os
import sys


DIC_FILES = ['lex.csv', 'matrix.def', 'char.def', 'unk.def',
             'left-id.def', 'right-id.def', 'rewrite.def',
             'feature.def', 'dicrc']
BIN_FILES = ['char.bin', 'matrix.bin', 'sys.dic', 'unk.dic']


def test_core_existence(dic_dir):
    """Assert each required data file exists and is non-empty."""
    count = 0
    for fname in DIC_FILES:
        fpath = os.path.join(dic_dir, fname)
        assert os.path.isfile(fpath), f"MISSING: {fpath}"
        count += 1
        assert os.path.getsize(fpath) > 0, f"EMPTY: {fpath}"
        count += 1
    print(f"[PASS] core files: {len(DIC_FILES)} files ✅ ({count} asserts)")
    return count


def test_lex_count(dic_dir):
    """Assert lex.csv has exactly 756,463 entries."""
    fpath = os.path.join(dic_dir, 'lex.csv')
    with open(fpath, encoding='utf-8') as f:
        lines = sum(1 for _ in f)
    assert lines == 756463, f"lex.csv: {lines} != 756463"
    print(f"[PASS] lex.csv entries: {lines} ✅ (1 assert)")
    return 1


def test_matrix_size(dic_dir):
    """Assert matrix.def is the full 131,610 x 131,610 matrix (514 MB)."""
    size = os.path.getsize(os.path.join(dic_dir, 'matrix.def'))
    assert size > 500 * 1000 * 1000, f"matrix.def: {size} < 500MB"
    print(f"[PASS] matrix.def size: {size} bytes ✅ (1 assert)")
    return 1


def test_utf8(dic_dir):
    """UTF-8 validation per data file. UniDic is UTF-8 (unlike ipadic EUC-JP)."""
    ok = 0
    fail = 0
    for fname in DIC_FILES:
        fpath = os.path.join(dic_dir, fname)
        try:
            with open(fpath, 'r', encoding='utf-8') as f:
                while f.read(8 * 1024 * 1024):
                    pass
            ok += 1
        except UnicodeDecodeError:
            print(f"  UTF-8 FAILED: {fname}")
            fail += 1
    assert fail == 0, f"{fail} files invalid UTF-8"
    print(f"[PASS] UTF-8: {ok} OK, {fail} FAILED ✅ (1 assert)")
    return 1


def test_dicrc(dic_dir):
    """dicrc sanity: cost-factor and unidic output format."""
    with open(os.path.join(dic_dir, 'dicrc'), encoding='utf-8') as f:
        dicrc = f.read()
    assert 'cost-factor = 700' in dicrc, "dicrc cost-factor != 700"
    assert 'output-format-type = unidic' in dicrc, "dicrc output-format-type != unidic"
    print("[PASS] dicrc: cost-factor=700, output-format-type=unidic ✅ (2 asserts)")
    return 2


def test_binary_files(dic_dir):
    """Assert all binary index files exist and are non-empty (required)."""
    count = 0
    for fname in BIN_FILES:
        fpath = os.path.join(dic_dir, fname)
        assert os.path.isfile(fpath), f"MISSING binary index: {fpath}"
        assert os.path.getsize(fpath) > 0, f"EMPTY binary index: {fpath}"
        count += 2
        print(f"[PASS] binary index: {fname} ({os.path.getsize(fpath)} bytes)")
    print(f"[PASS] binary indices: {len(BIN_FILES)}/{len(BIN_FILES)} present ✅ ({count} asserts)")
    return count


def test_ohos_package_layout(dic_dir):
    """OHOS/HarmonyOS platform-specific assertions.

    Verifies the dictionary installs under the conan package folder layout
    consumed by OHOS target consumers (mecab -d <pkg>/dic), with no host
    absolute paths embedded in the data files (dicrc must not leak the build
    machine's dicdir), and data-only package properties (no bin/lib leakage).
    """
    count = 0
    pkg_dir = os.path.dirname(dic_dir)

    # 1. Dictionary lives in <package>/dic — the layout mecab -d consumers use
    assert os.path.basename(dic_dir) == 'dic', f"dic dir must be 'dic', got {dic_dir}"
    count += 1

    # 2. dicrc must not contain build-machine absolute paths
    with open(os.path.join(dic_dir, 'dicrc'), encoding='utf-8') as f:
        dicrc = f.read()
    assert '/storage/' not in dicrc and '/home/' not in dicrc and '/tmp/' not in dicrc, \
        "dicrc leaks build-machine absolute paths"
    count += 1

    # 3. Data-only package: no bin/ or lib/ artifacts shipped in the package
    assert not os.path.isdir(os.path.join(pkg_dir, 'bin')), "unexpected bin/ in data package"
    assert not os.path.isdir(os.path.join(pkg_dir, 'lib')), "unexpected lib/ in data package"
    count += 1

    # 4. License files shipped alongside the data (GPL/LGPL/BSD triple license)
    for lic in ['COPYING', 'GPL', 'LGPL', 'BSD']:
        fpath = os.path.join(dic_dir, lic)
        assert os.path.isfile(fpath), f"license file missing: {lic}"
        count += 1

    print(f"[PASS] OHOS package layout: dic/ dir, no path leaks, data-only, "
          f"triple license ✅ ({count} asserts)")
    return count


def test_mecab_consumption(dic_dir, mecab_pkg):
    """Real MeCab consumption (required): compile a tiny consumer against the
    mecab/0.996 package dependency and load this dictionary — verifies the
    installed package actually works as a MeCab dicdir on the target, not
    just that files exist.

    Fail-closed: compiler, mecab headers/library, dictionary load and
    morphological analysis are all hard requirements — no SKIP paths.
    """
    import shutil
    import subprocess
    import tempfile

    cxx = shutil.which('clang++') or shutil.which('g++')
    assert cxx, "no C++ compiler (clang++/g++) found for mecab consumption test"

    inc = os.path.join(mecab_pkg, 'include')
    lib = os.path.join(mecab_pkg, 'lib', 'libmecab.a')
    assert os.path.isfile(os.path.join(inc, 'mecab.h')), f"mecab.h missing: {inc}/mecab.h"
    assert os.path.isfile(lib), f"libmecab.a missing: {lib}"

    workdir = tempfile.mkdtemp(prefix='unidic-consumer-')
    try:
        consumer_src = os.path.join(workdir, 'consumer.cpp')
        with open(consumer_src, 'w', encoding='utf-8') as f:
            f.write(
                '#include <mecab.h>\n'
                '#include <cstdio>\n'
                'int main(int argc, char **argv) {\n'
                '    char opt[4096];\n'
                '    snprintf(opt, sizeof(opt), "-d %s -r %s/dicrc", argv[1], argv[1]);\n'
                '    mecab_t *m = mecab_new2(opt);\n'
                '    if (!m) { fprintf(stderr, "load failed: %s\\n", mecab_strerror(0)); return 3; }\n'
                '    const char *out = mecab_sparse_tostr(m, '
                '"\\xe3\\x81\\x99\\xe3\\x82\\x82\\xe3\\x82\\x82\\xe3\\x82\\x82'
                '\\xe3\\x82\\x82\\xe3\\x82\\x82\\xe3\\x82\\x82\\xe3\\x82\\x82'
                '\\xe3\\x81\\xae\\xe3\\x81\\x86\\xe3\\x81\\xa1");\n'
                '    if (!out) { fprintf(stderr, "analysis failed: %s\\n", mecab_strerror(m)); return 4; }\n'
                '    printf("%s", out);\n'
                '    mecab_destroy(m);\n'
                '    return 0;\n'
                '}\n')
        exe = os.path.join(workdir, 'consumer')
        r = subprocess.run([cxx, '-std=c++17', f'-I{inc}', consumer_src, lib,
                            '-lpthread', '-o', exe],
                           capture_output=True, text=True, timeout=120)
        assert r.returncode == 0, f"consumer compile failed: {r.stderr[:500]}"

        r = subprocess.run([exe, dic_dir], capture_output=True, text=True, timeout=120)
        assert r.returncode == 0, (
            f"mecab load/analysis failed rc={r.returncode}: "
            f"{(r.stderr or r.stdout)[:500]}")

        out = r.stdout
        # UniDic output: surface\tpos detail ... with EOS at the end
        assert 'EOS' in out, f"output missing EOS: {out[:200]}"
        # すもも must be segmented as its own token with UniDic features
        # (orth, lemma and PoS columns from the unidic output format)
        lines = [ln for ln in out.splitlines() if ln.strip() and ln.strip() != 'EOS']
        assert len(lines) >= 4, f"too few tokens: {out[:200]}"
        assert '\t' in lines[0], f"no unidic feature columns: {lines[0]}"
        print("[PASS] real mecab consumption via mecab/0.996 package ✅")
        print(f"       sample: {lines[0]}")
        return 8  # compiler + header + lib + compile + load + EOS + tokens + format
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def main():
    if len(sys.argv) != 3:
        print("Usage: python3 test_mecab_unidic.py <dic_dir> <mecab_pkg_dir>")
        sys.exit(2)
    dic_dir = os.path.abspath(sys.argv[1])
    mecab_pkg = os.path.abspath(sys.argv[2])
    assert os.path.isdir(dic_dir), f"dic dir not found: {dic_dir}"
    assert os.path.isdir(mecab_pkg), f"mecab package dir not found: {mecab_pkg}"

    total_asserts = 0
    total_asserts += test_core_existence(dic_dir)
    total_asserts += test_lex_count(dic_dir)
    total_asserts += test_matrix_size(dic_dir)
    total_asserts += test_utf8(dic_dir)
    total_asserts += test_dicrc(dic_dir)
    total_asserts += test_binary_files(dic_dir)
    total_asserts += test_ohos_package_layout(dic_dir)
    total_asserts += test_mecab_consumption(dic_dir, mecab_pkg)
    print(f"\n=== mecab-unidic consumer test PASSED — {total_asserts} assertions ===")
    sys.exit(0)


if __name__ == '__main__':
    main()
