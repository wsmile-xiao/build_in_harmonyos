#!/usr/bin/env python3
"""Test for argparse-manpage: generate manpage and verify output.

This test:
1. Creates a Python file with an argparse.ArgumentParser
2. Runs argparse-manpage to generate a man page
3. Verifies the output contains expected sections and arguments
"""
import os
import shutil
import subprocess
import sys


def main():
    # Create a test Python file with an argparse parser
    tmpdir = os.environ.get("TMPDIR", os.path.expanduser("~/tmp"))
    os.makedirs(tmpdir, exist_ok=True)
    test_py = os.path.join(tmpdir, "test_parser_amp.py")
    with open(test_py, "w") as f:
        f.write(
            "import argparse\n"
            "\n"
            "def get_parser():\n"
            "    p = argparse.ArgumentParser(\n"
            "        prog='testprog',\n"
            "        description='A test program for manpage generation'\n"
            "    )\n"
            "    p.add_argument('--input', '-i', help='Input file',\n"
            "                   required=True)\n"
            "    p.add_argument('--output', '-o', help='Output file')\n"
            "    p.add_argument('--verbose', '-v', action='store_true',\n"
            "                   help='Verbose output')\n"
            "    return p\n"
        )

    # Find argparse-manpage in PATH
    am = shutil.which("argparse-manpage")
    if not am:
        print("❌ argparse-manpage not found in PATH")
        sys.exit(1)

    print(f"Found argparse-manpage at: {am}")

    # Run argparse-manpage to generate a man page
    result = subprocess.run(
        [am, "--pyfile", test_py, "--function", "get_parser",
         "--project-name", "testprog", "--version", "1.0"],
        capture_output=True, text=True
    )

    if result.returncode != 0:
        print(f"❌ argparse-manpage failed: {result.stderr}")
        sys.exit(1)

    manpage = result.stdout

    # Assertion 1: manpage contains NAME section
    assert ".SH NAME" in manpage, "NAME section not found in manpage output"
    print("✅ Assertion 1 passed: NAME section found")

    # Assertion 2: manpage contains SYNOPSIS section
    assert ".SH SYNOPSIS" in manpage, "SYNOPSIS section not found"
    print("✅ Assertion 2 passed: SYNOPSIS section found")

    # Assertion 3: manpage contains OPTIONS section
    assert ".SH OPTIONS" in manpage, "OPTIONS section not found"
    print("✅ Assertion 3 passed: OPTIONS section found")

    # Assertion 4: manpage contains the --input argument
    assert "--input" in manpage, "--input argument not found"
    print("✅ Assertion 4 passed: --input argument found")

    # Assertion 5: manpage contains the --verbose argument
    assert "--verbose" in manpage, "--verbose argument not found"
    print("✅ Assertion 5 passed: --verbose argument found")

    print("\n✅ All tests passed!")


if __name__ == "__main__":
    main()
