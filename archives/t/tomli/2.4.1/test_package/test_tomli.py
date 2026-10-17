#!/usr/bin/env python3
"""Conan test_package for tomli — verifies module + real usage.

R34: tomli/ module files present in site-packages and import + real
tomli.loads call works (parse TOML string).
"""
import os
import subprocess
import sys

TEST_SCRIPT = r'''
import sys
sys.path.insert(0, "{site}")
import tomli
# 真实调用：tomli.loads 解析 TOML 字符串
data = tomli.loads('key = 42\n[table]\nname = "x"\n')
print("tomli smoke: key=%d table=%s" % (data["key"], data["table"]["name"]))
assert data["key"] == 42 and data["table"]["name"] == "x"
print("OK: tomli import + real loads works")
'''


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    site = os.path.join(pkg, "lib", "python3.12", "site-packages")
    if not os.path.isdir(os.path.join(site, "tomli")):
        print(f"FAIL: tomli module missing: {site}", file=sys.stderr)
        return 1
    required = ["__init__.py", "_parser.py", "_re.py"]
    missing = [f for f in required
               if not os.path.isfile(os.path.join(site, "tomli", f))]
    if missing:
        print(f"FAIL: tomli files missing: {missing}", file=sys.stderr)
        return 1
    r = subprocess.run(
        [sys.executable, "-c", TEST_SCRIPT.replace("{site}", site)],
        capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FAIL: import/run: {r.stderr}", file=sys.stderr)
        return 1
    print(r.stdout.strip())
    print("OK: tomli module + real loads usage works")
    return 0


if __name__ == "__main__":
    sys.exit(main())
