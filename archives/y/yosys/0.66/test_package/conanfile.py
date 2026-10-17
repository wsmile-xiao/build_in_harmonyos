#!/usr/bin/env python3
"""Conan test_package for yosys 0.66 — L1 consumer test.

yosys is a CLI tool (RTL synthesis), not a library, so this test executes the
installed binary instead of linking against it:
  1. yosys -V                          -> the version banner
  2. a real synthesis of test.v        -> read_verilog + synth + stat
The synthesis also exercises the external ABC binary wired in through
ABCEXTERNAL / ABC, which is the decisive part of this recipe.

File location: archives/y/yosys/0.66/test_package/conanfile.py
"""
import os
import shutil

from conan import ConanFile


def _first_existing(*candidates):
    """Return the first candidate that is an existing absolute path."""
    for cand in candidates:
        if cand and os.path.exists(cand):
            return cand
    return None


class YosysTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _cc(self):
        # The harness only needs to spawn the yosys binary, so any working C
        # compiler does.  Prefer the profile toolchain (on the OHOS device that
        # is the SDK clang), then $CC, then a PATH lookup — a stale device path
        # must not break the test on a developer machine.
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict) or {}
        found = _first_existing(compilers.get("c"), os.environ.get("CC"))
        if found:
            return found
        for name in ("clang", "cc", "gcc"):
            found = shutil.which(name)
            if found:
                return found
        return "cc"

    def _bash(self):
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries, so wrap the
        # invocation with bash (same pattern as the abc test_package).
        return _first_existing(os.environ.get("CONFIG_SHELL"),
                               "/data/service/hnp/bin/bash",
                               "/bin/bash", "/usr/bin/bash") or "bash"

    def build(self):
        self.run(f"{self._cc()} test.c -o test_yosys")

    def test(self):
        self.run(f"{self._bash()} -c './test_yosys'", env="conanrun")
