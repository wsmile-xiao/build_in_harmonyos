#!/usr/bin/env python3
"""mkcue consumer test cases (run against the *packaged* binary).

Upstream mkcue ships **no automated test suite**: the tarball has no
``tests/`` directory and ``GNUmakefile.in`` has no ``check``/``test``
target (see ``../reports/upstream-test-entry.md``).  The cases below are
therefore derived from documented, observable upstream behaviour:

* ``README:7-10`` — default device is ``/dev/cdrom``, an optional device
  argument overrides it, and ``-t track-count`` limits the listed tracks.
* ``mkcue.cc:30-52`` — argument validation: ``-t`` must be 1..99, unknown
  options print the usage line ``mkcue [-t track-count] [device]`` and
  exit 2, and failing to open the device is reported on stderr with exit 2.

Because no optical device (nor its CDROM ioctls) exists in a build/CI
sandbox, the reachable and verifiable surface is the argument/device
error path; the TOC-reading happy path requires real CD hardware and is
recorded as untestable rather than silently skipped.

OHOS platform cases (>=1, R: 鸿蒙特有用例) verify that the packaged
artifact is a loadable HarmonyOS image (AArch64 ELF with the OHOS musl
interpreter and a ``.codesign`` section, knowledge base E077).
"""

import argparse
import os
import shutil
import subprocess
import sys

# ── helpers ────────────────────────────────────────────────────────────────

def _tool(name, fallback):
    found = shutil.which(name)
    if found:
        return found
    if os.path.isfile(fallback):
        return fallback
    return None


def _run(argv, cwd=None):
    proc = subprocess.run(
        argv, cwd=cwd, capture_output=True, text=True, errors="replace", timeout=60
    )
    return proc.returncode, proc.stdout, proc.stderr


class Case:
    def __init__(self, name, kind, fn):
        self.name = name
        self.kind = kind
        self.fn = fn

    def run(self):
        """Return (status, detail); status in {PASS, FAIL, SKIP}."""
        try:
            return self.fn()
        except Exception as exc:  # noqa: BLE001 - test harness reports everything
            return "FAIL", f"exception: {exc!r}"


# ── cases ──────────────────────────────────────────────────────────────────

def build_cases(binary, readelf):
    cases = []

    def cli_case(name, argv, expect_rc, needles):
        def _fn():
            rc, out, err = _run([binary] + argv)
            blob = out + err
            if rc != expect_rc:
                return "FAIL", f"rc={rc} (expected {expect_rc}); stdout+stderr={blob!r}"
            for needle in needles:
                if needle not in blob:
                    return "FAIL", f"missing {needle!r} in {blob!r}"
            return "PASS", f"rc={rc}; output matched {needles!r}"
        cases.append(Case(name, "upstream-behaviour", _fn))

    # Documented default device (README:7): no CD in the sandbox -> open fails, exit 2.
    cli_case("upstream-default-device-open-error", [], 2, ["Cannot open '/dev/cdrom'"])
    # Documented optional device argument (README:8).
    cli_case(
        "upstream-explicit-device-open-error",
        ["/nonexistent-device"],
        2,
        ["Cannot open '/nonexistent-device'"],
    )
    # Argument validation (mkcue.cc:36-43): -t must be 1..99.
    cli_case("upstream-trackcount-zero-rejected", ["-t", "0"], 2, ["invalid track-count 0"])
    cli_case("upstream-trackcount-over-99-rejected", ["-t", "100"], 2, ["invalid track-count 100"])
    cli_case("upstream-trackcount-one-accepted", ["-t", "1", "/nonexistent-device"], 2, ["Cannot open '/nonexistent-device'"])
    # Unknown option -> usage line, exit 2 (mkcue.cc:44-46).
    cli_case("upstream-unknown-option-usage", ["-x"], 2, ["mkcue [-t track-count] [device]"])

    # ── OHOS platform cases ───────────────────────────────────────────────
    def ohos_machine():
        if readelf is None:
            return "FAIL", "llvm-readelf not found; cannot verify OHOS ELF"
        rc, out, err = _run([readelf, "-h", binary])
        if rc != 0:
            return "FAIL", f"readelf rc={rc}: {err.strip()}"
        if "AArch64" not in out:
            return "FAIL", "ELF machine is not AArch64"
        return "PASS", "ELF Machine: AArch64"
    cases.append(Case("ohos-elf-aarch64", "ohos-platform", ohos_machine))

    def ohos_codesign():
        if readelf is None:
            return "FAIL", "llvm-readelf not found; cannot verify .codesign"
        rc, out, err = _run([readelf, "-S", binary])
        if rc != 0:
            return "FAIL", f"readelf rc={rc}: {err.strip()}"
        if ".codesign" not in out:
            return "FAIL", "ELF has no .codesign section (E077: OHOS will refuse to load it)"
        return "PASS", ".codesign section present"
    cases.append(Case("ohos-elf-codesign-section", "ohos-platform", ohos_codesign))

    def ohos_interp():
        if readelf is None:
            return "FAIL", "llvm-readelf not found; cannot verify interpreter"
        rc, out, err = _run([readelf, "-l", binary])
        if rc != 0:
            return "FAIL", f"readelf rc={rc}: {err.strip()}"
        if "ld-musl-aarch64.so.1" not in out:
            return "FAIL", "interpreter is not the OHOS musl loader"
        return "PASS", "interpreter: /lib/ld-musl-aarch64.so.1"
    cases.append(Case("ohos-elf-musl-interpreter", "ohos-platform", ohos_interp))

    return cases


# ── main ───────────────────────────────────────────────────────────────────

def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("bin_dir", help="package bin/ directory")
    parser.add_argument("--log", default=None, help="write the case log here")
    args = parser.parse_args(argv)

    binary = os.path.join(args.bin_dir, "mkcue")
    readelf = _tool("llvm-readelf", "/data/service/hnp/bin/llvm-readelf")

    lines = []
    lines.append(f"# mkcue consumer test — bin_dir={args.bin_dir}")
    lines.append(f"# binary={binary} exists={os.path.isfile(binary)}")
    lines.append(f"# readelf={readelf}")

    if not os.path.isfile(binary):
        lines.append("FATAL: packaged binary not found")
        _flush(lines, args.log)
        print("\n".join(lines))
        return 1

    passed = failed = skipped = 0
    for case in build_cases(binary, readelf):
        status, detail = case.run()
        lines.append(f"[{status}] ({case.kind}) {case.name}: {detail}")
        if status == "PASS":
            passed += 1
        elif status == "SKIP":
            skipped += 1
        else:
            failed += 1

    lines.append("")
    lines.append(f"TOTAL={passed + failed + skipped} PASS={passed} FAIL={failed} SKIP={skipped}")
    _flush(lines, args.log)
    print("\n".join(lines))
    return 1 if failed else 0


def _flush(lines, log):
    if not log:
        return
    os.makedirs(os.path.dirname(log), exist_ok=True)
    with open(log, "w", encoding="utf-8") as fh:
        fh.write("\n".join(lines) + "\n")


if __name__ == "__main__":
    sys.exit(main())
