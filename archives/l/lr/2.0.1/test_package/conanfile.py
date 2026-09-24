#!/usr/bin/env python3
"""test_package for lr 2.0.1 — binary-level functional tests for the packaged executable.

Upstream lr ships no test suite (no test target in the Makefile, no test
files, no CI).  test_lr.sh supplements that gap with CLI assertions whose
expectations were captured from real lr 2.0.1 behavior on this OHOS host,
plus an OHOS-specific block verifying the packaged ELF itself (ELF64/LSB/
AArch64 ABI, PIE, musl interpreter, libc.so-only deps, no RPATH/RUNPATH).
"""
from conan import ConanFile


class LrTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # /bin/sh on this OHOS host executes the packaged ELF fine (verified
        # live: `sh -c './lr -1 DIR'` runs).  The harmonybrew bash injected
        # via CONFIG_SHELL is unreliable on HMDFS (E386 family), so use
        # /bin/sh directly — same approach as the merged lrcalc 1.2 package.
        self.run("/bin/sh test_lr.sh", env="conanrun")
