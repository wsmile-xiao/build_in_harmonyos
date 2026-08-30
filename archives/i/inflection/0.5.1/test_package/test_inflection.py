#!/usr/bin/env python3
"""inflection consumer test (R34): module importable from package site-packages
+ real inflection API usage (pluralize/singularize/camelize/underscore)."""
import os
import subprocess
import sys

SMOKE_PY = r'''
import sys
sys.path[0:0] = __import__("os").environ["PYTHONPATH"].split(":")
import inflection
print("inflection imported")

from inflection import pluralize, singularize, camelize, underscore

# 真实 API：单词变形
assert pluralize("person") == "people"
assert singularize("people") == "person"
assert camelize("employee_salary") == "EmployeeSalary"
assert underscore("EmployeeSalary") == "employee_salary"

print("OK: inflection pluralize/singularize/camelize/underscore works")
'''


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    site = os.path.join(pkg, "lib", "python3.12", "site-packages")
    mod = os.path.join(site, "inflection", "__init__.py")
    if not os.path.isfile(mod):
        print(f"FAIL: inflection module missing: {mod}", file=sys.stderr)
        return 1
    env = dict(os.environ)
    env["PYTHONPATH"] = site
    # 用调用本脚本的 python（必然存在且可执行——沙箱 PATH 无 python3 实测）
    py = sys.executable
    r = subprocess.run([py, "-c", SMOKE_PY], capture_output=True,
                       text=True, env=env)
    if r.returncode != 0:
        print(f"FAIL: inflection API: {r.stderr}", file=sys.stderr)
        return 1
    print(r.stdout.strip())
    print("OK: inflection module + word inflection real API works")
    return 0


if __name__ == "__main__":
    sys.exit(main())
