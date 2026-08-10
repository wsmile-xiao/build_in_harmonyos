#!/usr/bin/env python3
"""test_aspell_en.py — validate aspell-en English dictionary data files.

This script exercises the actual packaged content of aspell-en.
It validates:
1. en.dat exists and is non-empty (dictionary metadata)
2. en.dat contains 'name en' (confirms English dictionary)
3. en.rws or .cwl word list files exist (compiled/raw dictionary data)
4. en.multi exists (multi-file alias configuration)
5. Package contains English-specific content in .dat files
6. en.dat contains a charset declaration (e.g. 'charset iso-8859-1')
7. Dictionary data files are present (.cwt, .wsn, .cwl, .dat, .multi, .alias)
8. Count total data files installed (should be >= 5)

Exit 0 on success, non-zero on failure with clear error message.
"""
import os
import sys


def find_package_root():
    """Get the package folder from command line argument."""
    if len(sys.argv) < 2:
        print("FAIL: Usage: test_aspell_en.py <package_folder>")
        sys.exit(1)
    return sys.argv[1]


def find_data_dirs(pkg_root):
    """Find the dictionary and data directories within the package."""
    # Standard layout: res/dict and res/data
    dict_dir = os.path.join(pkg_root, "res", "dict")
    data_dir = os.path.join(pkg_root, "res", "data")

    # Fallback: search for en.dat anywhere in the package
    if not os.path.isdir(dict_dir):
        for root, dirs, files in os.walk(pkg_root):
            if "en.dat" in files:
                data_dir = root
                dict_dir = root
                break

    return dict_dir, data_dir


def test_en_dat_exists(data_dir):
    """Test 1: Verify en.dat exists and is non-empty."""
    en_dat = os.path.join(data_dir, "en.dat")
    if not os.path.exists(en_dat):
        print(f"FAIL: en.dat not found in {data_dir}")
        return False
    if os.path.getsize(en_dat) == 0:
        print("FAIL: en.dat is empty")
        return False
    print(f"PASS: en.dat exists and is non-empty ({os.path.getsize(en_dat)} bytes)")
    return True


def test_en_dat_name(data_dir):
    """Test 2: Verify en.dat contains 'name en'."""
    en_dat = os.path.join(data_dir, "en.dat")
    with open(en_dat, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    if "name en" not in content:
        print("FAIL: en.dat does not contain 'name en'")
        return False
    print("PASS: en.dat contains 'name en' — English dictionary confirmed")
    return True


def test_word_list_files(dict_dir):
    """Test 3: Verify .cwl word list files exist (raw dictionary data)."""
    cwl_files = [f for f in os.listdir(dict_dir) if f.endswith(".cwl")]
    rws_files = [f for f in os.listdir(dict_dir) if f.endswith(".rws")]
    if len(cwl_files) == 0 and len(rws_files) == 0:
        print("FAIL: No .cwl or .rws dictionary data files found")
        return False
    total = len(cwl_files) + len(rws_files)
    print(f"PASS: Found {total} dictionary data files "
          f"({len(cwl_files)} .cwl, {len(rws_files)} .rws)")
    return True


def test_en_multi_exists(dict_dir):
    """Test 4: Verify en.multi exists (multi-file alias configuration)."""
    en_multi = os.path.join(dict_dir, "en.multi")
    if not os.path.exists(en_multi):
        print(f"FAIL: en.multi not found in {dict_dir}")
        return False
    with open(en_multi, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    if len(content.strip()) == 0:
        print("FAIL: en.multi is empty")
        return False
    print(f"PASS: en.multi exists and is non-empty ({os.path.getsize(en_multi)} bytes)")
    return True


def test_english_content(data_dir):
    """Test 5: Verify .dat files contain English-specific content."""
    dat_files = [f for f in os.listdir(data_dir) if f.endswith(".dat")]
    if len(dat_files) == 0:
        print("FAIL: No .dat files found in data directory")
        return False
    found_english = False
    for dat_file in dat_files:
        dat_path = os.path.join(data_dir, dat_file)
        with open(dat_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read().lower()
        if "name en" in content or "english" in content:
            found_english = True
            break
    if not found_english:
        print("FAIL: No English-specific content found in .dat files")
        return False
    print(f"PASS: Found English-specific content in {len(dat_files)} .dat file(s)")
    return True


def test_charset_declaration(data_dir):
    """Test 6: Verify en.dat contains a charset declaration."""
    en_dat = os.path.join(data_dir, "en.dat")
    with open(en_dat, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()
    if "charset" not in content:
        print("FAIL: en.dat does not contain a charset declaration")
        return False
    print("PASS: en.dat contains charset declaration")
    return True


def test_dictionary_data_types(dict_dir, data_dir):
    """Test 7: Verify dictionary data files are present (.cwl, .dat, .multi, .alias)."""
    all_files = os.listdir(dict_dir) + os.listdir(data_dir)
    extensions_found = set()
    for f in all_files:
        if "." in f:
            ext = f.rsplit(".", 1)[-1]
            extensions_found.add(ext)
    expected_extensions = {"cwl", "dat", "multi", "alias"}
    found_expected = extensions_found & expected_extensions
    if len(found_expected) < 3:
        print(f"FAIL: Only found {found_expected} of expected extensions "
              f"{expected_extensions}")
        return False
    print(f"PASS: Found dictionary data types: {found_expected}")
    return True


def test_total_data_files(dict_dir, data_dir):
    """Test 8: Count total data files installed (should be >= 5)."""
    dict_files = [f for f in os.listdir(dict_dir)
                  if f.endswith((".cwl", ".rws", ".multi", ".alias"))]
    data_files = [f for f in os.listdir(data_dir)
                  if f.endswith((".dat", "info"))]
    total = len(dict_files) + len(data_files)
    if total < 5:
        print(f"FAIL: Only {total} data files found (expected >= 5)")
        return False
    print(f"PASS: Found {total} total data files "
          f"({len(dict_files)} dict, {len(data_files)} data)")
    return True


def main():
    pkg_root = find_package_root()
    dict_dir, data_dir = find_data_dirs(pkg_root)

    print(f"Package root: {pkg_root}")
    print(f"Dict directory: {dict_dir}")
    print(f"Data directory: {data_dir}")
    print()

    if not os.path.isdir(dict_dir):
        print(f"FAIL: Dictionary directory not found: {dict_dir}")
        sys.exit(1)
    if not os.path.isdir(data_dir):
        print(f"FAIL: Data directory not found: {data_dir}")
        sys.exit(1)

    tests = [
        ("en.dat exists", lambda: test_en_dat_exists(data_dir)),
        ("en.dat has name en", lambda: test_en_dat_name(data_dir)),
        ("word list files exist", lambda: test_word_list_files(dict_dir)),
        ("en.multi exists", lambda: test_en_multi_exists(dict_dir)),
        ("English content in .dat", lambda: test_english_content(data_dir)),
        ("charset declaration", lambda: test_charset_declaration(data_dir)),
        ("dictionary data types", lambda: test_dictionary_data_types(dict_dir, data_dir)),
        ("total data files >= 5", lambda: test_total_data_files(dict_dir, data_dir)),
    ]

    passed = 0
    failed = 0
    for test_name, test_func in tests:
        if test_func():
            passed += 1
        else:
            failed += 1

    print()
    print(f"Results: {passed}/{passed + failed} tests passed")
    if failed > 0:
        print(f"FAIL: {failed} test(s) failed")
        sys.exit(1)
    print("SUCCESS: All tests passed")
    sys.exit(0)


if __name__ == "__main__":
    main()
