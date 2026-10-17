#!/usr/bin/env python3
"""Test that ace-link.el is properly installed and contains expected content."""
import os
import sys

def main():
    pkg_dir = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    el_file = os.path.join(pkg_dir, "lib", "site-lisp", "ace-link.el")

    if not os.path.exists(el_file):
        sys.exit(f"ERROR: {el_file} not found")

    if os.path.getsize(el_file) == 0:
        sys.exit(f"ERROR: {el_file} is empty")

    with open(el_file, "r", encoding="utf-8", errors="replace") as f:
        content = f.read()

    if "(provide 'ace-link)" not in content:
        sys.exit(f"ERROR: {el_file} missing expected '(provide 'ace-link)' marker")

    print(f"PASS: {el_file} - {os.path.getsize(el_file)} bytes, contains (provide 'ace-link)")
    sys.exit(0)

if __name__ == "__main__":
    main()
