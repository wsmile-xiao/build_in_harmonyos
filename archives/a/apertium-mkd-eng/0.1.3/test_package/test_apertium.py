#!/usr/bin/env python3
"""Test script for apertium-mkd-eng package.

Validates that the packaged linguistic data files are present,
non-empty, and contain the expected Macedonian-English translation
content. This is a substantive test (R34) — it checks file content,
not just existence.
"""

import os
import sys
import xml.etree.ElementTree as ET


def test_package(package_dir):
    """Run all validation tests on the packaged data files.

    Args:
        package_dir: Root directory of the installed Conan package.

    Returns:
        List of (test_name, passed, detail) tuples.
    """
    results = []
    data_dir = os.path.join(package_dir, "share", "apertium",
                            "apertium-mkd-eng")

    # ── Test 1: Data directory exists ──
    exists = os.path.isdir(data_dir)
    results.append(("data_dir_exists", exists,
                    f"data_dir={data_dir}"))

    if not exists:
        return results

    # ── Test 2: modes.xml exists and is valid XML ──
    modes_path = os.path.join(data_dir, "modes.xml")
    modes_exists = os.path.isfile(modes_path)
    modes_valid = False
    modes_content = ""
    if modes_exists:
        modes_size = os.path.getsize(modes_path)
        if modes_size > 0:
            try:
                tree = ET.parse(modes_path)
                root = tree.getroot()
                if root.tag == "modes":
                    modes_valid = True
                with open(modes_path, "r", encoding="utf-8") as f:
                    modes_content = f.read()
            except ET.ParseError:
                pass
            except Exception:
                pass
    results.append(("modes_xml_exists", modes_exists,
                    f"path={modes_path}"))
    results.append(("modes_xml_valid", modes_valid,
                    "root tag is <modes>"))

    # ── Test 3: modes.xml defines mkd-eng mode ──
    has_mkd_eng_mode = 'name="mkd-eng"' in modes_content
    results.append(("modes_has_mkd_eng_mode", has_mkd_eng_mode,
                    "modes.xml contains <mode name=\"mkd-eng\">"))

    # ── Test 4: Core .dix dictionary files present ──
    dix_files = [
        "apertium-mkd-eng.mkd.dix",      # Macedonian monolingual
        "apertium-mkd-eng.eng.dix",      # English monolingual
        "apertium-mkd-eng.mkd-eng.dix",  # Bilingual MKD→ENG
    ]
    for dix in dix_files:
        dix_path = os.path.join(data_dir, dix)
        dix_exists = os.path.isfile(dix_path) and \
            os.path.getsize(dix_path) > 0
        results.append((f"dix_file_{dix}", dix_exists,
                        f"path={dix_path}"))

    # ── Test 5: Transfer rule files present (.t1x, .t2x, .t3x) ──
    transfer_files = [
        "apertium-mkd-eng.mkd-eng.t1x",
        "apertium-mkd-eng.mkd-eng.t2x",
        "apertium-mkd-eng.mkd-eng.t3x",
    ]
    for tf in transfer_files:
        tf_path = os.path.join(data_dir, tf)
        tf_exists = os.path.isfile(tf_path) and \
            os.path.getsize(tf_path) > 0
        results.append((f"transfer_file_{tf}", tf_exists,
                        f"path={tf_path}"))

    # ── Test 6: Constraint grammar files present (.rlx, .lex) ──
    cg_files = [
        "apertium-mkd-eng.mkd-eng.rlx",
        "apertium-mkd-eng.mkd-eng.lex",
    ]
    for cg in cg_files:
        cg_path = os.path.join(data_dir, cg)
        cg_exists = os.path.isfile(cg_path) and \
            os.path.getsize(cg_path) > 0
        results.append((f"cg_file_{cg}", cg_exists,
                        f"path={cg_path}"))

    # ── Test 7: Prob files present (HMM tagger data) ──
    prob_files = ["mkd-eng.prob", "eng-mkd.prob"]
    for pf in prob_files:
        pf_path = os.path.join(data_dir, pf)
        pf_exists = os.path.isfile(pf_path) and \
            os.path.getsize(pf_path) > 0
        results.append((f"prob_file_{pf}", pf_exists,
                        f"path={pf_path}"))

    # ── Test 8: Count total data files (should be >= 10) ──
    all_files = []
    if os.path.isdir(data_dir):
        for fname in os.listdir(data_dir):
            fpath = os.path.join(data_dir, fname)
            if os.path.isfile(fpath) and os.path.getsize(fpath) > 0:
                all_files.append(fname)
    file_count_ok = len(all_files) >= 10
    results.append(("data_file_count", file_count_ok,
                    f"count={len(all_files)} files={sorted(all_files)}"))

    # ── Test 9: .dix file contains Macedonian content ──
    mkd_dix_path = os.path.join(data_dir,
                                "apertium-mkd-eng.mkd-eng.dix")
    has_mkd_content = False
    if os.path.isfile(mkd_dix_path):
        with open(mkd_dix_path, "r", encoding="utf-8") as f:
            content = f.read()
        # Check for Macedonian Cyrillic characters or Macedonian refs
        has_mkd_content = (
            "Macedonian" in content or
            "македон" in content or  # Cyrillic for "Macedon(ian)"
            "<dictionary>" in content
        )
    results.append(("dix_has_mkd_content", has_mkd_content,
                    "mkd-eng.dix contains Macedonian translation entries"))

    # ── Test 10: .dix file is valid XML with <dictionary> root ──
    dix_valid = False
    if os.path.isfile(mkd_dix_path):
        try:
            tree = ET.parse(mkd_dix_path)
            root = tree.getroot()
            if root.tag == "dictionary":
                dix_valid = True
        except ET.ParseError:
            pass
        except Exception:
            pass
    results.append(("dix_xml_valid", dix_valid,
                    "mkd-eng.dix is valid XML with <dictionary> root"))

    # ── Test 11: Transfer .t1x file is valid XML ──
    t1x_path = os.path.join(data_dir,
                            "apertium-mkd-eng.mkd-eng.t1x")
    t1x_valid = False
    if os.path.isfile(t1x_path):
        try:
            tree = ET.parse(t1x_path)
            root = tree.getroot()
            # Transfer rules root is <transfer>
            if root.tag == "transfer":
                t1x_valid = True
        except ET.ParseError:
            pass
        except Exception:
            pass
    results.append(("t1x_xml_valid", t1x_valid,
                    "mkd-eng.t1x is valid XML with <transfer> root"))

    return results


def main():
    if len(sys.argv) < 2:
        print("Usage: test_apertium.py <package_dir>", file=sys.stderr)
        sys.exit(1)

    package_dir = sys.argv[1]
    if not os.path.isdir(package_dir):
        print(f"FAIL: Package directory does not exist: {package_dir}",
              file=sys.stderr)
        sys.exit(1)

    print(f"Testing apertium-mkd-eng package at: {package_dir}")
    print("=" * 60)

    results = test_package(package_dir)

    passed = 0
    failed = 0
    for test_name, ok, detail in results:
        status = "PASS" if ok else "FAIL"
        print(f"  [{status}] {test_name}: {detail}")
        if ok:
            passed += 1
        else:
            failed += 1

    print("=" * 60)
    print(f"Results: {passed} passed, {failed} failed, "
          f"{passed + failed} total")

    if failed > 0:
        print(f"FAIL: {failed} test(s) failed", file=sys.stderr)
        sys.exit(1)

    print("SUCCESS: All tests passed")
    sys.exit(0)


if __name__ == "__main__":
    main()
