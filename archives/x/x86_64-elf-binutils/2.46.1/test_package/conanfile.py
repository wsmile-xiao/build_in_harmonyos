#!/usr/bin/env python3
"""Conan test_package — x86_64-elf-binutils 2.46.1.

Exercises the cross-toolchain end to end: assemble a minimal x86_64-elf
program with x86_64-elf-as, then verify the resulting object with
x86_64-elf-readelf (machine = x86-64), x86_64-elf-objdump (disassembly) and
x86_64-elf-ar (archiving). The tools run on the build host and operate on
x86_64 ELF objects (R34: the package binaries are genuinely invoked, not a
stub).
"""
import os

from conan import ConanFile


class X8664ElfBinutilsTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot exec ELF binaries; wrap with bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'"{bash}" test.sh', env="conanrun")
