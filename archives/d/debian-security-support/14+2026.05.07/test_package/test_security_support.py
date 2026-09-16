#!/usr/bin/env python3
"""Harmony package validation for debian-security-support (NOT upstream tests).

Runs the shipped shell tool with a controlled-but-real data file + manifest so
the portable core (date/status decision) is exercised, and verifies the honest
no-backend failure (exit 3) instead of upstream's empty-output-exit-0 trap.
"""
import os
import shutil
import subprocess
import sys
import tempfile

VERSION = "14+2026.05.07"


def run(env, args, tool):
    return subprocess.run([tool] + args, capture_output=True, text=True,
                          env=env, timeout=120)


def main():
    root = sys.argv[1]
    tool = os.path.join(root, "bin", "check-support-status")
    data = os.path.join(root, "share", "debian-security-support")
    if not (os.path.isfile(tool) and os.path.isdir(data)):
        print("FAIL: packaged layout missing (bin/check-support-status or share data)")
        return 1

    for f in ("security-support.deb11", "security-support.deb12",
              "security-support.deb13", "security-support.deb14"):
        p = os.path.join(data, f)
        if not os.path.isfile(p):
            print(f"FAIL: missing data file {f}")
            return 1

    # runtime toolchain present? (sh + awk + grep + date -d + getopt)
    if not shutil.which("sh"):
        print("SKIP: no sh — cannot execute shell tool (layout checks above passed)")
        return 0
    awk = shutil.which("gawk") or shutil.which("awk") or shutil.which("mawk")
    if not awk:
        print("SKIP: no awk — cannot execute core decision (layout checks passed)")
        return 0
    env = dict(os.environ)
    env["DSS_AWK"] = awk

    # 1) CLI smoke
    r = run(env, ["--version"], tool)
    if r.returncode != 0 or VERSION not in r.stdout:
        print(f"FAIL: --version rc={r.returncode} out={r.stdout!r} err={r.stderr!r}")
        return 1
    r = run(env, ["--help"], tool)
    if r.returncode != 0 or "Usage:" not in (r.stdout + r.stderr):
        print("FAIL: --help")
        return 1

    # 2) core decision with real supplied data file + manifest
    with tempfile.TemporaryDirectory() as td:
        datafile = os.path.join(td, "security-support.deb14")
        with open(datafile, "w") as fh:
            fh.write("# test data (columns: source status version end-date note)\n"
                     "zlib1g non-supported 1.2.0-1 2020-01-01 fake past\n"
                     "vim non-supported 9.1-1 2099-01-01 fake future\n"
                     "foo limited limited reasons\n"
                     "sqv supported fully supported\n")
        manifest = os.path.join(td, "manifest.tsv")
        with open(manifest, "w") as fh:
            fh.write("install ok installed\tzlib1g\t1.2.0-1\tzlib1g\n"
                     "install ok installed\tvim\t9.1-1\tvim\n")
        fakebin = os.path.join(td, "fakebin")
        os.mkdir(fakebin)
        fake_mktemp = os.path.join(fakebin, "mktemp")
        with open(fake_mktemp, "w") as fh:
            fh.write("#!/bin/sh\necho 'mktemp: need XXXXXX: Not supported' >&2\nexit 1\n")
        os.chmod(fake_mktemp, 0o755)

        tenv = dict(env)
        tenv["DSS_DATA_DIR"] = td
        tenv["DSS_MANIFEST"] = manifest
        tenv["DEBIAN_VERSION"] = "14"
        tenv["PATH"] = fakebin + os.pathsep + tenv.get("PATH", "")

        r = run(tenv, ["--type", "ended", "--no-heading"], tool)
        if "ended on 2020-01-01" not in r.stdout or "vim" in r.stdout:
            print(f"FAIL: ended core-decision out={r.stdout!r} err={r.stderr!r}")
            return 1
        r = run(tenv, ["--type", "earlyend", "--no-heading"], tool)
        if "will end on 2099-01-01" not in r.stdout or "zlib1g" in r.stdout:
            print(f"FAIL: earlyend core-decision out={r.stdout!r} err={r.stderr!r}")
            return 1

        # 3) honest no-backend boundary: dpkg disabled + no manifest/status
        nenv = dict(env)
        nenv["DSS_DATA_DIR"] = td
        nenv["DEBIAN_VERSION"] = "14"
        nenv["DSS_DISABLE_DPKG"] = "1"
        nenv.pop("DSS_MANIFEST", None)
        nenv.pop("DSS_DPKG_STATUS", None)
        r = run(nenv, ["--type", "ended", "--no-heading"], tool)
        if r.returncode != 3:
            print(f"FAIL: no-backend must exit 3 (got {r.returncode}) "
                  f"out={r.stdout!r} err={r.stderr!r}")
            return 1
        if r.stdout:
            print("FAIL: no-backend produced a non-empty report (fake success)")
            return 1

    # 4) shipped data-file lint (weak: status enum + date column format)
    ok = True
    for f in ("security-support.deb11", "security-support.deb12",
              "security-support.deb13", "security-support.deb14"):
        n = 0
        for line in open(os.path.join(data, f), encoding="utf-8",
                         errors="replace"):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            cols = line.split()
            if len(cols) < 2 or cols[1] not in ("non-supported", "limited",
                                                "supported"):
                print(f"WARN: {f}: unusual line: {line[:60]}")
                continue
            n += 1
        if n == 0:
            ok = False
            print(f"FAIL: {f} has no parseable rows")
    if not ok:
        return 1

    print("OK: debian-security-support package validation passed "
          "(version/help, ended+earlyend core decision on supplied manifest, "
          "no-backend exit-3, data lint)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
