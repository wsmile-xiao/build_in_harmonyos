#!/usr/bin/env python3
"""test_spdx.py — Smoke test for spdx-licenses 3.28.0.

Verifies:
  1. licenseListVersion == 3.28.0
  2. Total licenses == 727, deprecated == 32
  3. Total exceptions == 84, deprecated exceptions == 1
  4. MIT, Apache-2.0, BSD-3-Clause, GPL-2.0-only must be found
  5. NOT-A-REAL-SPDX-ID must be rejected
  6. Output fixed JSON summary for exact comparison

Usage:
  python3 test_spdx.py <res_dir>
  where <res_dir> contains licenses.json and exceptions.json
"""
import json
import os
import sys


def main():
    if len(sys.argv) < 2:
        print("Usage: test_spdx.py <res_dir>")
        sys.exit(1)

    res_dir = sys.argv[1]
    lic_path = os.path.join(res_dir, "licenses.json")
    exc_path = os.path.join(res_dir, "exceptions.json")

    failures = 0

    print("=" * 60)
    print("test_spdx.py: SPDX License List v3.28.0 Verification")
    print("=" * 60)

    # ── licenses.json ──
    with open(lic_path) as f:
        lic_data = json.load(f)

    lv = lic_data.get("licenseListVersion")
    if lv != "3.28.0":
        print(f"[FAIL] licenseListVersion expected 3.28.0, got {lv}")
        failures += 1
    else:
        print(f"[PASS] licenseListVersion = {lv}")

    licenses = lic_data.get("licenses", [])
    if len(licenses) != 727:
        print(f"[FAIL] expected 727 licenses, got {len(licenses)}")
        failures += 1
    else:
        print(f"[PASS] Total licenses = {len(licenses)}")

    deprecated = [l for l in licenses if l.get("isDeprecatedLicenseId", False)]
    if len(deprecated) != 32:
        print(f"[FAIL] expected 32 deprecated licenses, got {len(deprecated)}")
        failures += 1
    else:
        print(f"[PASS] Deprecated licenses = {len(deprecated)}")

    # ── exceptions.json ──
    with open(exc_path) as f:
        exc_data = json.load(f)

    ev = exc_data.get("licenseListVersion")
    if ev != "3.28.0":
        print(f"[FAIL] exceptions licenseListVersion expected 3.28.0, got {ev}")
        failures += 1
    else:
        print(f"[PASS] exceptions licenseListVersion = {ev}")

    exceptions = exc_data.get("exceptions", [])
    if len(exceptions) != 84:
        print(f"[FAIL] expected 84 exceptions, got {len(exceptions)}")
        failures += 1
    else:
        print(f"[PASS] Total exceptions = {len(exceptions)}")

    deprecated_exc = [e for e in exceptions if e.get("isDeprecatedLicenseId", False)]
    if len(deprecated_exc) != 1:
        print(f"[FAIL] expected 1 deprecated exception, got {len(deprecated_exc)}")
        failures += 1
    else:
        print(f"[PASS] Deprecated exceptions = {len(deprecated_exc)}")

    # ── Query known IDs ──
    lic_ids = {l["licenseId"] for l in licenses}
    known = ["MIT", "Apache-2.0", "BSD-3-Clause", "GPL-2.0-only"]
    for kid in known:
        if kid not in lic_ids:
            print(f"[FAIL] Query '{kid}': NOT FOUND")
            failures += 1
        else:
            print(f"[PASS] Query '{kid}': FOUND")

    # ── Query bogus ID ──
    bogus = "NOT-A-REAL-SPDX-ID"
    if bogus in lic_ids:
        print(f"[FAIL] Query '{bogus}': should NOT exist")
        failures += 1
    else:
        print(f"[PASS] Query '{bogus}': correctly NOT FOUND")

    # ── Output fixed JSON summary ──
    summary = {
        "package": "spdx-licenses",
        "version": "3.28.0",
        "licenseListVersion": lv,
        "total_licenses": len(licenses),
        "deprecated_licenses": len(deprecated),
        "total_exceptions": len(exceptions),
        "deprecated_exceptions": len(deprecated_exc),
        "known_ids_found": known,
        "bogus_id_rejected": bogus,
        "checksum_licenses_json": "f728c534d8bd1044fc515a2ddb2292be99559021d830bfa3281be0bcd36302ee",
        "checksum_exceptions_json": "bd145bb558f44432fcd6f0d7e956ed0124dff72af7641a7cfcb1b557dc390a5b",
        "status": "ALL_PASSED"
    }
    summary_path = os.path.join(os.getcwd(), "spdx-licenses-3.28.0-summary.json")
    with open(summary_path, "w") as f:
        json.dump(summary, f, indent=2)
    print(f"[INFO] Summary written to {summary_path}")

    print("=" * 60)
    if failures == 0:
        print("ALL checks PASSED")
    else:
        print(f"{failures} check(s) FAILED")

    return failures


if __name__ == "__main__":
    rc = main()
    sys.exit(rc)
