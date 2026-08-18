#!/usr/bin/env python3
"""Conan test_package — riscv64-elf-gdb 17.2.

Exercises the cross-debugger via the riscv64-elf-gdb command family
(R34: the package binary is genuinely invoked, not a stub). The actual
test flow (test_package/test.sh) issues four riscv64-elf-gdb -batch
invocations that verify: (1) --version prints "GNU gdb ... 17.2";
(2) set architecture riscv:rv64 followed by show architecture confirms
rv64 support; (3) maintenance print architecture emits the internal
GDB architecture description; (4) show data-directory reports the
loaded data directory. No assembly (riscv64-elf-as), no ELF load, and
no disassembly are performed — the test validates the debugger binary
itself rather than exercising a riscv64 target object. Avoids
ptrace/attach (E222).
"""
import os

from conan import ConanFile


class Riscv64ElfGdbTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # OHOS /system/bin/sh (mksh) cannot exec ELF binaries; wrap with bash.
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f'"{bash}" test.sh', env="conanrun")
