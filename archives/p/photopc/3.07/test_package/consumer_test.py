#!/usr/bin/env python3
"""Consumer test source for photopc 3.07 (invoked by conanfile.py test()).

Usage: consumer_test.py <bindir> <outdir>
Runs the packaged photopc/epinfo binaries with behavior assertions.
"""
import os
import shlex
import subprocess
import sys


def run_capture(cmd, name, outdir):
    # subprocess (not os.system) so the terminating signal, when any, is read
    # from a structured negative returncode instead of a wait-status word --
    # CI evidence 2026-09-26 build#61474: epinfo died of SIGHUP right after
    # printing the expected banner, and the shell redirection made that
    # indistinguishable from a clean exit.  Signal deaths map to 200+sig so
    # every accepted set {0,1}/!=0 fails loudly; stdout+stderr land in `out`.
    out = os.path.join(outdir, name)
    with open(out, "w", encoding="utf-8", errors="replace") as sink:
        proc = subprocess.run(cmd, shell=True, stdout=sink,
                              stderr=subprocess.STDOUT, timeout=120)
    rc = proc.returncode
    code = 200 - rc if rc < 0 else rc
    with open(out, encoding="utf-8", errors="replace") as fh:
        return code, fh.read()


def main():
    if len(sys.argv) < 3:
        print("usage: consumer_test.py <bindir> <outdir>")
        return 2
    bindir, outdir = sys.argv[1], sys.argv[2]
    photopc = os.path.join(bindir, "photopc")
    epinfo = os.path.join(bindir, "epinfo")
    failures = 0

    # 1. epinfo -V: version banner.
    rc, out = run_capture(shlex.quote(epinfo) + " -V", "version.txt", outdir)
    if rc != 0 or "version 3.07" not in out:
        print("FAIL epinfo -V: rc=%s out=%r" % (rc, out[:120]))
        failures += 1

    # 2. epinfo parsing path: non-EPSON file is walked and reported
    #    (documented behavior: exit code 1 when no camera info found).
    probe = os.path.join(outdir, "probe.bin")
    with open(probe, "wb") as f:
        f.write(b"DS-12 photopc consumer probe payload\n" * 4)
    rc, out = run_capture(
        "%s %s" % (shlex.quote(epinfo), shlex.quote(probe)), "parse.txt", outdir
    )
    # Exit code: worker/OHOS builds return 0 on this informational path while
    # some desktop builds return 1; upstream epinfo exits 0 unless another
    # error path fires.  The behavior under test is the parse-and-report path,
    # asserted on the emitted message; rc is pinned to {0,1} so a crash
    # (signal/other codes) still fails.  CI evidence 2026-09-24: rc=0 +
    # message on worker, rc=1 locally.
    if rc not in (0, 1) or "No camera-specific information" not in out:
        print("FAIL epinfo parse: rc=%s out=%r" % (rc, out[:120]))
        failures += 1

    # 3. epinfo usage on missing args.
    rc, out = run_capture(shlex.quote(epinfo), "usage.txt", outdir)
    if "epinfo" not in out or "[-V]" not in out:
        print("FAIL epinfo usage: rc=%s out=%r" % (rc, out[:120]))
        failures += 1

    # 4. photopc device-open/termios error path (no camera attached).
    rc, out = run_capture(shlex.quote(photopc), "openerr.txt", outdir)
    if "open" not in out or "eph_open failed" not in out:
        print("FAIL photopc open path: rc=%s out=%r" % (rc, out[:160]))
        failures += 1

    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
