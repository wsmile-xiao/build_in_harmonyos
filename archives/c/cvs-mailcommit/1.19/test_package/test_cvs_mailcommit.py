#!/usr/bin/env python3
"""cvs-mailcommit 1.19 consumer test — installed Perl script verification.

Three real assertions (R34: must exercise the delivered script):
  1) bin/cvs-mailcommit exists and is executable;
  2) `perl -c` syntax check passes (proves it is a valid Perl program);
  3) the script runs (`--help` when supported, else bare invocation with
     piped empty stdin) and produces output without a Perl compilation
     error — proves the installed file is runnable, not a stub.

Emits the HMBS machine-evidence marker with true discovered/passed counts.
Exits non-zero on any failure so conan create fails closed.
"""
import json
import os
import shutil
import subprocess
import sys


def find_perl():
    """Locate a runnable perl without hardcoding a single absolute path.

    Prefer $PERL / toolchain perl over PATH perl: preflight showed PATH
    perl (.harmonybrew/bin/perl) forking as OOM.
    """
    cand = os.environ.get("PERL")
    if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
        return cand
    for p in ("/data/service/hnp/bin/perl",
              "/usr/bin/perl", "/bin/perl", "/usr/local/bin/perl"):
        if os.path.isfile(p) and os.access(p, os.X_OK):
            return p
    for name in ("perl", "perl5"):
        p = shutil.which(name)
        if p:
            return p
    return "perl"


def run(cmd, stdin_data=None):
    proc = subprocess.run(
        cmd, input=stdin_data, capture_output=True, text=True, timeout=60)
    return proc


def main():
    pkg_root = sys.argv[1] if len(sys.argv) > 1 else "."
    discovered = 3
    passed = 0

    script = os.path.join(pkg_root, "bin", "cvs-mailcommit")
    if not os.path.isfile(script):
        print("[FAIL] bin/cvs-mailcommit missing in %s" % pkg_root)
        print('HMBS_TEST_PACKAGE_RESULT=%s' % json.dumps({
            "executed": True, "passed": False, "command": "python3 test_cvs_mailcommit.py <pkg>",
            "discovered": discovered, "passedCount": 0}))
        return 1
    if not os.access(script, os.X_OK):
        print("[FAIL] bin/cvs-mailcommit is not executable")
        print('HMBS_TEST_PACKAGE_RESULT=%s' % json.dumps({
            "executed": True, "passed": False, "command": "python3 test_cvs_mailcommit.py <pkg>",
            "discovered": discovered, "passedCount": 0}))
        return 1
    print("[ok] 1/3 bin/cvs-mailcommit exists and is executable")
    passed += 1

    perl = find_perl()
    try:
        proc = run([perl, "-c", script])
    except OSError as exc:
        print("[FAIL] 2/3 cannot execute perl (%s): %s" % (perl, exc))
        print('HMBS_TEST_PACKAGE_RESULT=%s' % json.dumps({
            "executed": True, "passed": False, "command": "python3 test_cvs_mailcommit.py <pkg>",
            "discovered": discovered, "passedCount": passed}))
        return 1
    combined = (proc.stdout or "") + (proc.stderr or "")
    if proc.returncode != 0 or "syntax OK" not in combined:
        print("[FAIL] 2/3 perl -c syntax check failed:\n%s" % combined.strip())
        print('HMBS_TEST_PACKAGE_RESULT=%s' % json.dumps({
            "executed": True, "passed": False, "command": "python3 test_cvs_mailcommit.py <pkg>",
            "discovered": discovered, "passedCount": passed}))
        return 1
    print("[ok] 2/3 perl -c syntax OK")
    passed += 1

    # Functional run: prefer --help, fall back to -h, then bare run with
    # empty stdin. Accept any invocation that does not die with a Perl
    # compilation error; the script normally prints usage and exits.
    exercised = False
    last_out = ""
    for args in (["--help"], ["-h"], []):
        try:
            proc = run([perl, script] + args, stdin_data="")
        except OSError as exc:
            last_out = "cannot execute perl (%s): %s" % (perl, exc)
            break
        last_out = (proc.stdout or "") + (proc.stderr or "")
        if "Can't locate" in last_out or "syntax error" in last_out:
            continue
        if last_out.strip():
            exercised = True
            print("[ok] 3/3 script runs with args %s, output %d bytes" % (args, len(last_out.strip())))
            break
    if not exercised:
        print("[FAIL] 3/3 script produced no usable output:\n%s" % last_out.strip())
        print('HMBS_TEST_PACKAGE_RESULT=%s' % json.dumps({
            "executed": True, "passed": False, "command": "python3 test_cvs_mailcommit.py <pkg>",
            "discovered": discovered, "passedCount": passed}))
        return 1
    passed += 1

    print("cvs-mailcommit package OK (%d/%d)" % (passed, discovered))
    print('HMBS_TEST_PACKAGE_RESULT=%s' % json.dumps({
        "executed": True, "passed": True, "command": "python3 test_cvs_mailcommit.py <pkg>",
        "discovered": discovered, "passedCount": passed}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
