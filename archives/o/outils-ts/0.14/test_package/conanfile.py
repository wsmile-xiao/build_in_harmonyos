#!/usr/bin/env python3
"""test_package for outils-ts 0.14 — binary-level functional tests.

Upstream outils 0.14 ships NO automated test suite: none of the 13 Makefiles
has a test/check/regress target, there is no tests/ directory and no CI
configuration, and the ts component itself contains only ts.c + ts.1
(R51 inventory, evidence in ../reports/upstream-test-inventory.log).

test_ts.sh supplements that gap.  Every expectation below was captured from
the real packaged binary on this OHOS host before being written down.  It
also contains the HarmonyOS-specific checks:
  * the reallocarray(3) growth path of ts — the very code path that the
    OHOS portability patch exists for (OHOS musl libc lacks reallocarray);
  * the packaged ELF's ABI/loader/dependency shape (AArch64 PIE, musl
    interpreter, sole NEEDED entry libc.so, no RPATH/RUNPATH).
"""
from conan import ConanFile


class OutilsTsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # /bin/sh on this OHOS host executes the packaged aarch64 PIE fine.
        self.run("/bin/sh test_ts.sh", env="conanrun")
