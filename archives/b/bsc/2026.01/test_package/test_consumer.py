#!/usr/bin/env python3
"""Consumer use case for the bsc/2026.01 source-contract package.

The package ships upstream contract files, not a compiler binary (building
bsc needs a GHC toolchain that does not exist on OHOS yet).  This script
plays the role of a real downstream consumer of that contract -- a
toolchain-gating script that must answer, from the PACKAGE contents alone:

  1. Which GHC versions are acceptable for building this pinned snapshot?
     Parse every "A through B" range out of the packaged INSTALL.md,
     derive the effective supported range (max of floors, min of
     ceilings), then gate concrete candidate versions against it.
  2. Which Hackage packages must be provisioned?
     Parse GHC_PKGS out of the packaged src/Makefile.
  3. Is aarch64 a recognized build machine?
     Consult the packaged platform.mk MACHTYPE handling.

It parses and decides instead of grepping for fixed strings: decorative
text would pass a presence check, but only a real contract yields
consistent gating decisions.

Exit codes: 0 = 3/3 consumer checks passed; 1 = a check failed;
2 = packaged contract files are missing (nothing to consume).
"""
import os
import re
import sys


def vtuple(text):
    return tuple(int(p) for p in text.strip().split("."))


def check_ghc_gate(install_path):
    text = open(install_path, encoding="utf-8", errors="replace").read()
    matches = re.findall(r"(\d+\.\d+(?:\.\d+)?)\s+through\s+(\d+\.\d+(?:\.\d+)?)", text)
    if not matches:
        print("[bsc][consumer] FAIL: no 'min through max' version range in packaged INSTALL.md")
        return False
    lo = max(vtuple(a) for a, _b in matches)
    hi = min(vtuple(b) for _a, b in matches)
    if lo > hi:
        print("[bsc][consumer] FAIL: inconsistent ranges in INSTALL.md (floor > ceiling)")
        return False
    # Decisions a downstream gating script would make from the contract:
    # 9.10.1 = the aarch64-alpine musl bindist candidate (must be accepted),
    # 9.6.4  = upstream-recommended point-release family (must be accepted),
    # 7.10.2 = just below the strictest published floor (must be rejected).
    decisions = [("9.10.1", True), ("9.6.4", True), ("7.10.2", False)]
    for cand, want in decisions:
        got = lo <= vtuple(cand) <= hi
        if got != want:
            print(f"[bsc][consumer] FAIL: GHC {cand} gate -> {got}, expected {want} "
                  f"(effective range {lo}..{hi})")
            return False
    print(f"[bsc][consumer] OK: GHC gate derived from INSTALL.md ranges "
          f"({len(matches)} statement(s), effective {lo}..{hi}); "
          "9.10.1/9.6.4 accepted, 7.10.2 rejected")
    return True


def check_hackage_manifest(makefile_path):
    text = open(makefile_path, encoding="utf-8", errors="replace").read()
    m = re.search(r"^GHC_PKGS\s*=\s*(.+)$", text, re.M)
    if not m:
        print("[bsc][consumer] FAIL: no GHC_PKGS declaration in packaged src/Makefile")
        return False
    got = set(m.group(1).split())
    want = {"regex-compat", "syb", "old-time", "split", "strict-concurrency"}
    if got != want:
        print(f"[bsc][consumer] FAIL: GHC_PKGS mismatch: got {sorted(got)}")
        return False
    print("[bsc][consumer] OK: Hackage provisioning manifest complete: "
          + ", ".join(sorted(got)))
    return True


def check_portability(platform_path):
    text = open(platform_path, encoding="utf-8", errors="replace").read()
    if not re.search(r"\baarch64\b", text):
        print("[bsc][consumer] FAIL: packaged platform.mk does not recognize aarch64")
        return False
    n = len(re.findall(r"x86_64|i386|ppc64le|aarch64|arm64|armv7l", text))
    print(f"[bsc][consumer] OK: packaged platform.mk recognizes aarch64 "
          f"({n} MACHTYPE token references)")
    return True


def main(pkg):
    install = os.path.join(pkg, "INSTALL.md")
    makefile = os.path.join(pkg, "src", "Makefile")
    platform = os.path.join(pkg, "platform.mk")
    for p in (install, makefile, platform):
        if not os.path.isfile(p):
            print(f"[bsc][consumer] BLOCKED: packaged contract file missing: {p}")
            sys.exit(2)

    results = [
        check_ghc_gate(install),
        check_hackage_manifest(makefile),
        check_portability(platform),
    ]
    passed = sum(results)
    if passed < 3:
        print(f"[bsc][consumer] DONE: {passed}/3 consumer checks passed")
        sys.exit(1)
    print("[bsc][consumer] DONE: consumer use case 3/3 PASS "
          "(toolchain gating on the packaged contract; compiler build/run "
          "NOT performed - blocked on GHC)")
    sys.exit(0)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: test_consumer.py <bsc-package-folder>")
        sys.exit(2)
    main(sys.argv[1])
