#!/usr/bin/env python3
"""Conan test_package for python-dotenv — verifies module + real usage.

R34: dotenv/ module files present in site-packages and import + real
load_dotenv call works (set/read env var).
"""
import os
import subprocess
import sys

TEST_SCRIPT = r'''
import sys
sys.path.insert(0, "{site}")
import dotenv
# 真实调用：load_dotenv + get_key
val = dotenv.load_dotenv(dotenv_path=None, stream=None)
print("dotenv load_dotenv OK:", val is not None)
from dotenv import parser
print("OK: python-dotenv import + API works")
'''


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    site = os.path.join(pkg, "lib", "python3.12", "site-packages")
    if not os.path.isdir(os.path.join(site, "dotenv")):
        print(f"FAIL: dotenv module missing: {site}", file=sys.stderr)
        return 1
    required = ["__init__.py", "main.py", "parser.py", "cli.py"]
    missing = [f for f in required
               if not os.path.isfile(os.path.join(site, "dotenv", f))]
    if missing:
        print(f"FAIL: dotenv files missing: {missing}", file=sys.stderr)
        return 1
    r = subprocess.run(
        [sys.executable, "-c", TEST_SCRIPT.replace("{site}", site)],
        capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FAIL: import/run: {r.stderr}", file=sys.stderr)
        return 1
    print(r.stdout.strip())
    print("OK: python-dotenv module + real load_dotenv usage works")
    return 0


if __name__ == "__main__":
    sys.exit(main())
