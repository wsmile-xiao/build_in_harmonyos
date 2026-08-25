#!/usr/bin/env python3
"""test_package/test_btest.py — btest 1.0.0 verification.

Invoked as:  python3 test_btest.py <package_folder>
Exits 0 on PASS, 1 on FAIL.

All assertions are real (not stubs):
  1. main driver script bin/btest exists
  2. all 12 expected scripts exist in bin/
  3. every python script passes py_compile syntax check
     (cfile redirected to a temp dir under the verifier's
     own folder, because the installed package tree is read-only)
  4. COPYING license file exists at share/btest/COPYING
"""
import os
import sys
import tempfile
import py_compile

BC_ROOT = sys.argv[1] if len(sys.argv) > 1 else ""
if not BC_ROOT:
    print("FAIL: usage: test_btest.py <package_folder>")
    sys.exit(1)

BIN_DIR = os.path.join(BC_ROOT, "bin")
LAUNCHER = os.path.join(BIN_DIR, "btest")
LICENSE = os.path.join(BC_ROOT, "share", "btest", "COPYING")

failures = []


def check(cond, msg):
    if not cond:
        failures.append(msg)


# 1. main driver exists
check(os.path.isfile(LAUNCHER), f"btest script not found at {LAUNCHER}")

# 2. all 12 expected scripts exist
EXPECTED = [
    "btest",
    "btest-ask-update",
    "btest-bg-run",
    "btest-bg-run-helper",
    "btest-bg-wait",
    "btest-diff",
    "btest-progress",
    "btest-setsid",
    "btest-sphinx-diff-rst",
    "btest-sphinx-rst-cmd",
    "btest-sphinx-rst-include",
    "btest-sphinx-rst-pipe",
]
script_count = 0
for s in EXPECTED:
    p = os.path.join(BIN_DIR, s)
    if os.path.isfile(p):
        script_count += 1
    else:
        check(False, f"expected script {s} not found at {p}")

# 3. py_compile syntax check on every python script in bin/
#    cfile → temp dir (package tree is read-only on CI)
tmpdir = tempfile.mkdtemp(prefix="btest_pyc_")
try:
    for s in os.listdir(BIN_DIR):
        if not s.startswith("btest"):
            continue
        p = os.path.join(BIN_DIR, s)
        try:
            with open(p, "rb") as f:
                shebang = f.readline()
            if b"python" not in shebang:
                continue
            cfile = os.path.join(tmpdir, s + "c")
            py_compile.compile(p, cfile=cfile, doraise=True)
        except py_compile.PyCompileError as e:
            check(False, f"py_compile syntax error in {s}: {e}")
        except (IOError, OSError) as e:
            check(False, f"cannot read/compile {s}: {e}")
finally:
    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)

# 4. COPYING license exists
check(os.path.isfile(LICENSE), f"COPYING license not found at {LICENSE}")

if failures:
    for f in failures:
        print(f"FAIL: {f}")
    sys.exit(1)

print(f"PASS: btest package verified ({script_count} scripts, syntax OK)")
sys.exit(0)
