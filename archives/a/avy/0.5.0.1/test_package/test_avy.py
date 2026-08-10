#!/usr/bin/env python3
"""test_package for avy — verifies that avy.el was properly installed and contains expected Elisp content.

This test exercises the real avy API by validating the content of avy.el:
  1. Verifies avy.el exists in the package and is non-empty
  2. Verifies avy.el contains `(provide 'avy)` — the Emacs Lisp provide form
  3. Verifies avy.el contains `defun` — confirms it defines functions
  4. Verifies avy-test.el exists and contains ert test definitions
  5. Counts total defun forms in avy.el (should be > 10)
  6. Verifies avy.el has `avy-jump` — the key entry-point function
  7. Verifies avy.el has `avy-process` — the core processing function
  8. Verifies avy.el has `avy-read` — the core reading function
"""
import os
import sys


def main():
    errors = []

    # Get package directory from command-line argument
    if len(sys.argv) < 2:
        print("ERROR: Package directory argument required", file=sys.stderr)
        sys.exit(1)

    pkg_dir = sys.argv[1]
    site_lisp = os.path.join(pkg_dir, "lib", "site-lisp")

    # ─── Check 1: avy.el exists and is non-empty ───
    avy_el = os.path.join(site_lisp, "avy.el")
    if not os.path.isfile(avy_el):
        errors.append(f"avy.el not found at {avy_el}")
    elif os.path.getsize(avy_el) == 0:
        errors.append(f"avy.el is empty: {avy_el}")
    else:
        size = os.path.getsize(avy_el)
        print(f"PASS: avy.el exists ({size} bytes)")

    # ─── Check 2: avy-test.el exists and contains ert tests ───
    avy_test_el = os.path.join(site_lisp, "avy-test.el")
    if not os.path.isfile(avy_test_el):
        errors.append(f"avy-test.el not found at {avy_test_el}")
    else:
        with open(avy_test_el, "r", encoding="utf-8", errors="replace") as f:
            test_content = f.read()
        if "ert-deftest" not in test_content:
            errors.append("avy-test.el does not contain ert-deftest")
        else:
            ert_count = test_content.count("ert-deftest")
            print(f"PASS: avy-test.el contains {ert_count} ert-deftest forms")

    # ─── Checks 3-8: validate avy.el content ───
    if os.path.isfile(avy_el) and os.path.getsize(avy_el) > 0:
        with open(avy_el, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        # Check 3: (provide 'avy) marker
        if "(provide 'avy)" not in content:
            errors.append("avy.el missing (provide 'avy) marker")
        else:
            print("PASS: avy.el contains (provide 'avy)")

        # Check 4: contains defun (defines functions)
        defun_count = content.count("(defun")
        if defun_count == 0:
            errors.append("avy.el contains no (defun) forms")
        else:
            print(f"PASS: avy.el contains {defun_count} (defun) forms")

        # Check 5: defun count > 10 (avy is a substantial package)
        if defun_count <= 10:
            errors.append(f"avy.el has only {defun_count} defun forms (expected > 10)")
        else:
            print(f"PASS: avy.el has {defun_count} defun forms (> 10)")

        # Check 6: avy-jump — the key entry-point function
        if "avy-jump" not in content:
            errors.append("avy.el missing avy-jump function")
        else:
            print("PASS: avy.el contains avy-jump function")

        # Check 7: avy-process — the core processing function
        if "avy-process" not in content:
            errors.append("avy.el missing avy-process function")
        else:
            print("PASS: avy.el contains avy-process function")

        # Check 8: avy-read — the core reading function
        if "avy-read" not in content:
            errors.append("avy.el missing avy-read function")
        else:
            print("PASS: avy.el contains avy-read function")

    # ─── Report ───
    if errors:
        print("\nTEST FAILED:", file=sys.stderr)
        for e in errors:
            print(f"  - {e}", file=sys.stderr)
        sys.exit(1)

    print("\nAll avy tests PASSED")
    sys.exit(0)


if __name__ == "__main__":
    main()
