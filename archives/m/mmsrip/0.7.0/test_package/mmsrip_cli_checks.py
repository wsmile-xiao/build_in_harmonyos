#!/usr/bin/env python3
"""mmsrip 0.7.0 CLI test source — run by test_package/conanfile.py.

Invoked as:  mmsrip_cli_checks.py <path-to-mmsrip-binary>
Exit code 0 = all assertions passed.

All expectations were derived from the upstream 0.7.0 sources
(src/main.c, src/mms.c) before being asserted, and were re-verified
against the OHOS-built binary:

  1.  -v / --version → "mmsrip version 0.7.0" on stderr, exit 0
  2.  -a / --about   → program/authors/GPL banner, exit 0
  3.  -h / --help    → usage block incl. "-oFILE, --output=FILE", exit 0
  4.  no arguments   → usage printed, exit 1 (MMS_RET_ERROR → main
                       returns 1 via the clean: path)
  5.  http:// URL    → "bad protocol (mms:// was expected)", exit 1 —
                       rejected inside mms_create before any socket
  6.  mms://host (no path) → "url seems to be malformed", exit 1
  7.  -t mms://mmsrip.invalid/stream.asf → real gethostbyname/DNS
                       failure path → "unable to connect", exit 1, and
                       -t mode must not create stream.asf
  8.  -g FILE (alone) → debug log created containing the banner and
                       "debug log begins now"; the run itself then
                       fails with usage (exit 1) because no stream URL
                       follows. (-v returns 0 directly from inside the
                       getopt switch before -g is processed, so -g
                       must be exercised on its own.)
  9.  OHOS-specific: the binary is a dynamic ELF64 little-endian
                       aarch64 executable whose PT_INTERP is the musl
                       loader /lib/ld-musl-aarch64.so.1

No live MMS server is contacted; every network-adjacent path tested
is a deterministic failure path.
"""
import os
import re
import struct
import subprocess
import sys
import tempfile

MMSRIP = sys.argv[1] if len(sys.argv) > 1 else "mmsrip"
VERSION_LINE = "mmsrip version 0.7.0"
ABOUT_LINE = "mmsrip (MMS Ripper) version 0.7.0"
USAGE_LINE = "usage: mmsrip"


def run(args, cwd=None, stdin_devnull=True):
    """Run mmsrip, return (combined-output, exit-code). stdin is
    /dev/null so an accidental interactive prompt cannot hang the
    suite (defensive only — no path below reads stdin)."""
    kw = dict(
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
        text=True, timeout=60, check=False, cwd=cwd,
    )
    if stdin_devnull:
        with open(os.devnull, "rb") as devnull:
            return subprocess.run([MMSRIP] + args, stdin=devnull, **kw)
    return subprocess.run([MMSRIP] + args, **kw)


def check(cond, msg, detail=""):
    if not cond:
        print(f"FAIL: {msg}\n{detail}", file=sys.stderr)
        sys.exit(1)


def test_version():
    for flag in ("-v", "--version"):
        p = run([flag])
        check(p.returncode == 0, f"{flag} exit code {p.returncode} != 0")
        check(VERSION_LINE in p.stdout, f"{flag} banner missing", p.stdout)
    print("ok: version banner (-v/--version, exit 0)")


def test_about():
    for flag in ("-a", "--about"):
        p = run([flag])
        check(p.returncode == 0, f"{flag} exit code {p.returncode} != 0")
        check(ABOUT_LINE in p.stdout, f"{flag} about line missing", p.stdout)
        check("Nicolas BENOIT" in p.stdout, f"{flag} author line missing", p.stdout)
        check("GNU General Public License" in p.stdout, f"{flag} license line missing", p.stdout)
    print("ok: about banner (-a/--about, exit 0)")


def test_help():
    for flag in ("-h", "--help"):
        p = run([flag])
        check(p.returncode == 0, f"{flag} exit code {p.returncode} != 0")
        check(USAGE_LINE in p.stdout, f"{flag} usage line missing", p.stdout)
        check("-oFILE, --output=FILE" in p.stdout, f"{flag} options block missing", p.stdout)
    print("ok: usage block (-h/--help, exit 0)")


def test_noargs():
    p = run([])
    check(p.returncode == 1, f"no-args exit code {p.returncode} != 1")
    check(USAGE_LINE in p.stdout, "usage not printed for no args", p.stdout)
    print("ok: no arguments → usage, exit 1")


def test_bad_protocol():
    p = run(["http://stream.example.org/stream.asf"])
    check(p.returncode == 1, f"bad-protocol exit code {p.returncode} != 1")
    check("bad protocol (mms:// was expected)" in p.stdout,
          "protocol rejection message missing", p.stdout)
    print("ok: http:// URL rejected before any network activity, exit 1")


def test_malformed_url():
    p = run(["mms://stream.example.org"])
    check(p.returncode == 1, f"malformed-url exit code {p.returncode} != 1")
    check("url seems to be malformed" in p.stdout,
          "malformed-url message missing", p.stdout)
    print("ok: mms:// URL without path rejected, exit 1")


def test_unresolvable_host():
    with tempfile.TemporaryDirectory() as workdir:
        p = run(["-t", "mms://mmsrip.invalid/stream.asf"], cwd=workdir)
        check(p.returncode == 1, f"unresolvable -t exit code {p.returncode} != 1")
        check("unable to connect" in p.stdout,
              "connect failure message missing", p.stdout)
        check(not os.path.exists(os.path.join(workdir, "stream.asf")),
              "-t mode must not create an output file")
    print("ok: -t against unresolvable host → 'unable to connect', exit 1, no output file")


def test_debug_log():
    with tempfile.TemporaryDirectory() as workdir:
        dbg = os.path.join(workdir, "debug.log")
        p = run(["-g", dbg], cwd=workdir)
        check(p.returncode == 1, f"-g-only run exited {p.returncode} (expected usage exit 1)")
        check(os.path.isfile(dbg), "debug log not created")
        with open(dbg, encoding="utf-8", errors="replace") as f:
            content = f.read()
        check(ABOUT_LINE in content, "debug log banner missing", content)
        check("debug log begins now" in content,
              "debug log header missing", content)
    print("ok: -g debug log created and filled (run fails with usage, exit 1)")


def test_ohos_elf():
    """OHOS-specific: dynamic ELF64 LE aarch64 with the musl loader."""
    is_ohos = os.path.exists("/lib/ld-musl-aarch64.so.1")
    uname_rel = os.uname().release
    check(is_ohos or "HarmonyOS" not in uname_rel,
          "expected the OHOS musl loader on this device",
          f"uname={uname_rel}")
    with open(MMSRIP, "rb") as fh:
        head = fh.read(64)
    check(head[:4] == b"\x7fELF", "not an ELF binary")
    check(head[4] == 2, f"expected ELF64, got class {head[4]}")
    check(head[5] == 1, f"expected little-endian, got data {head[5]}")
    e_machine = struct.unpack("<H", head[18:20])[0]
    check(e_machine == 0xB7, f"expected EM_AARCH64 (183), got {e_machine}")
    with open(MMSRIP, "rb") as fh:
        blob = fh.read()
    m = re.search(rb"/lib/ld-musl-aarch64[^\x00]*", blob)
    check(m, "no musl aarch64 PT_INTERP string found in the binary")
    print(f"ok: OHOS ELF checks (ELF64 LE EM_AARCH64, interp {m.group(0).decode()})")


def main():
    check(os.path.isfile(MMSRIP) and os.access(MMSRIP, os.X_OK),
          f"mmsrip binary not found/executable: {MMSRIP!r}")
    test_version()
    test_about()
    test_help()
    test_noargs()
    test_bad_protocol()
    test_malformed_url()
    test_unresolvable_host()
    test_debug_log()
    test_ohos_elf()
    print("mmsrip 0.7.0: all CLI checks passed")


if __name__ == "__main__":
    main()
