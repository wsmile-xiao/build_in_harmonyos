#!/usr/bin/env python3
"""lsusb-laniksj 1.1.9 consumer test — script-only package verification.

Layers:
  1. Package layout: bin/lsusb present, executable, Bash shebang, not an ELF;
     man page, LICENSE and README packaged.
  2. HarmonyOS invariants: package is script-only (zero ELF files ⇒ no NEEDED
     dynamic dependencies and no host RPATH/RUNPATH can be introduced); the
     runtime Bash interpreter is itself a HarmonyOS AArch64 ELF64 executable
     and is new enough (>= 4) for extglob/here-strings.
  3. Upstream CI smoke executed for real: `./lsusb` — the exact command
     .github/workflows/lsusb-test.yml runs on macos-latest (upstream has no
     other formal tests).
  4. CLI behavior matrix in the target environment (exit codes / streams
     measured on HarmonyOS PC, 2026-09-20): default, -V, -h, -s, -d (with
     and without colon), -t, -v, -p and an invalid option.

Exits non-zero on any failure. Usage: test_lsusb.py <package_folder>
"""
import os
import re
import shutil
import subprocess
import sys

EXPECTED_VERSION_LINE = "lsusb for macOS 1.1.9"


def find_bash():
    # OHOS hnp bash lives in /data/service/hnp/bin (not in PATH) on some
    # workers; on-device bash is reachable via PATH (dehydrated precedent).
    bash = os.environ.get("BASH") or shutil.which("bash")
    if bash:
        return bash
    for candidate in ("/data/service/hnp/bin/bash", "/system/bin/bash",
                      "/usr/local/bin/bash"):
        if os.path.isfile(candidate):
            return candidate
    return None


def run(argv, cwd):
    # Pass PWD explicitly: some OHOS bash execution contexts lose getcwd().
    env = dict(os.environ)
    env["PWD"] = cwd
    return subprocess.run(argv, capture_output=True, text=True, env=env, cwd=cwd)


def main():
    pkg_root = sys.argv[1] if len(sys.argv) > 1 else "."
    failures = 0
    passed = 0

    def ok(msg):
        nonlocal passed
        passed += 1
        print("[ok] %s" % msg)

    def fail(msg):
        nonlocal failures
        failures += 1
        print("[FAIL] %s" % msg)

    # ── 1. Package layout ──────────────────────────────────────────────
    script = os.path.join(pkg_root, "bin", "lsusb")
    if not os.path.isfile(script):
        print("[FAIL] %s missing" % script)
        return 1
    ok("bin/lsusb present")

    if os.access(script, os.X_OK):
        ok("bin/lsusb is executable")
    else:
        fail("bin/lsusb is not executable (HMDFS chmod lost?)")

    with open(script, "rb") as f:
        head = f.read(64)
    first_line = head.split(b"\n", 1)[0]
    if head.startswith(b"#!") and b"bash" in first_line:
        ok("Bash shebang: %s" % first_line.decode("utf-8", "replace"))
    else:
        fail("unexpected shebang: %r" % first_line)

    if head[:4] == b"\x7fELF":
        fail("bin/lsusb must stay a Bash script, not an ELF binary")
    else:
        ok("bin/lsusb is a script, not ELF")

    for rel, desc in (("share/man/man8/lsusb.8", "man page"),
                      ("licenses/LICENSE", "license"),
                      ("share/doc/lsusb-laniksj/README.md", "README")):
        if os.path.isfile(os.path.join(pkg_root, rel)):
            ok("%s packaged (%s)" % (desc, rel))
        else:
            fail("%s missing (%s)" % (desc, rel))

    with open(os.path.join(pkg_root, "licenses", "LICENSE"),
              "rt", encoding="utf-8", errors="replace") as f:
        license_text = f.read()
    if "MIT" in license_text:
        ok("LICENSE is MIT")
    else:
        fail("LICENSE does not look like MIT")

    # ── 2. HarmonyOS invariants ─────────────────────────────────────────
    elf_files = []
    for root, _, files in os.walk(pkg_root):
        for name in files:
            path = os.path.join(root, name)
            try:
                with open(path, "rb") as f:
                    if f.read(4) == b"\x7fELF":
                        elf_files.append(path)
            except OSError:
                pass
    if elf_files:
        readelf = shutil.which("readelf")
        rpath_hits = []
        for path in elf_files:
            if readelf:
                proc = subprocess.run([readelf, "-d", path],
                                      capture_output=True, text=True)
                for line in proc.stdout.splitlines():
                    if "(RPATH)" in line or "(RUNPATH)" in line:
                        rpath_hits.append("%s: %s" % (path, line.strip()))
        fail("script-only package unexpectedly contains ELF: %s"
             % ", ".join(os.path.basename(p) for p in elf_files))
        if rpath_hits:
            fail("host RPATH/RUNPATH detected:\n  %s" % "\n  ".join(rpath_hits))
    else:
        ok("script-only package: 0 ELF files ⇒ no NEEDED dynamic deps, "
           "no host RPATH/RUNPATH")

    bash = find_bash()
    if not bash:
        fail("no Bash interpreter found (script needs bash >= 4)")
        print("lsusb-laniksj: %d assertion(s) failed" % failures)
        return 1
    ok("Bash interpreter: %s" % bash)

    readelf = shutil.which("readelf")
    with open(bash, "rb") as f:
        bash_is_elf = f.read(4) == b"\x7fELF"
    if bash_is_elf and readelf:
        proc = subprocess.run([readelf, "-h", bash],
                              capture_output=True, text=True)
        header = proc.stdout
        if re.search(r"Class:\s+ELF64", header) and \
                re.search(r"Machine:\s+AArch64", header):
            ok("interpreter is HarmonyOS AArch64 ELF64 "
               "(%s)" % os.path.basename(bash))
        else:
            fail("interpreter ELF header is not ELF64/AArch64:\n%s"
                 % header.strip())
    elif bash_is_elf:
        ok("interpreter is ELF (readelf unavailable, magic-only check)")
    else:
        fail("interpreter %s is not an ELF binary" % bash)

    proc = run([bash, "--version"], cwd=pkg_root)
    match = re.search(r"version (\d+)\.", proc.stdout)
    if proc.returncode == 0 and match and int(match.group(1)) >= 4:
        ok("Bash %s >= 4 (extglob capable)" % match.group(0))
    else:
        fail("Bash version check failed (rc=%d, output=%r)"
             % (proc.returncode, proc.stdout.strip()))

    # ── 3. Upstream CI smoke, executed for real ─────────────────────────
    proc = run([bash, "-n", script], cwd=pkg_root)
    if proc.returncode == 0:
        ok("bash -n syntax check OK")
    else:
        fail("bash -n syntax check failed:\n%s" % proc.stderr.strip())

    # Upstream .github/workflows/lsusb-test.yml runs exactly `./lsusb`.
    proc = run([bash, script], cwd=pkg_root)
    if proc.returncode == 0:
        ok("upstream CI smoke `./lsusb` rc=0 "
           "(no device data source ⇒ empty listing, exit 0)")
    else:
        fail("upstream CI smoke `./lsusb` failed (rc=%d):\n%s"
             % (proc.returncode, proc.stderr.strip()))

    # ── 4. CLI behavior matrix (measured on HarmonyOS PC) ───────────────
    # (argv, expected rc, expected stdout, expected first stderr line or
    #  None meaning stderr must be empty)
    cases = [
        ([],                  0, "", None),
        (["-V"],              0, EXPECTED_VERSION_LINE, None),
        (["-h"],              0, "", "Usage: lsusb [options]..."),
        (["-s", "001"],       1, "", None),
        (["-d", "05ac:1234"], 1, "", None),
        (["-d", "05ac"],      1, "", None),
        (["-t"],              0, "", None),
        (["-v"],              0, "", None),
        (["-p"],              0, "", None),
        (["-x"],              0, "", "lsusb: invalid option -- 'x'"),
    ]
    for argv, want_rc, want_out, want_err1 in cases:
        proc = run([bash, script] + argv, cwd=pkg_root)
        label = " ".join(argv) or "(default)"
        good = proc.returncode == want_rc
        if proc.stdout.strip() != want_out.strip():
            good = False
        err_lines = proc.stderr.splitlines()
        if want_err1 is None:
            if proc.stderr.strip() != "":
                good = False
        elif not err_lines or err_lines[0] != want_err1:
            good = False
        if good:
            ok("CLI %-14s rc=%d%s%s"
               % (label, want_rc,
                  " stdout=%r" % want_out if want_out else "",
                  " stderr=%r" % want_err1 if want_err1 else ""))
        else:
            fail("CLI %-14s: want rc=%d out=%r err1=%r, got rc=%d out=%r err=%r"
                 % (label, want_rc, want_out, want_err1, proc.returncode,
                    proc.stdout, proc.stderr))

    if failures:
        print("lsusb-laniksj: %d assertion(s) failed" % failures)
        return 1
    print("lsusb-laniksj: %d assertion(s) passed — package OK" % passed)
    return 0


if __name__ == "__main__":
    sys.exit(main())
