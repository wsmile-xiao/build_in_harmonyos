#!/usr/bin/env python3
"""Consumer test for the packaged i686-elf-gcc cross-compiler.

Verifies the installed compiler can compile and link a freestanding i686-elf
program, and that the resulting objects are genuine Intel 80386 ELF (R34: the
packaged binaries are really invoked, not stubbed).  The assembler/linker and
readelf/objdump come from the sibling i686-elf-binutils dependency, which is
propagated into PATH by VirtualRunEnv.
"""
import os

from conan import ConanFile


class I686ElfGccTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"
    exports_sources = "test.c", "test.sh"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot exec ELF binaries; wrap with bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'"{bash}" test.sh', env="conanrun")
