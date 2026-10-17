#!/usr/bin/env python3
"""Conan test_package for tinyice 2.6.3."""
import os
import struct

from conan import ConanFile
from conan.tools.build import can_run


class TinyiceTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def configure(self):
        self.settings.rm_safe("os.version")

    def _assert_aarch64_elf(self, path):
        if not os.path.isfile(path):
            raise RuntimeError(f"missing packaged binary: {path}")
        with open(path, "rb") as handle:
            magic = handle.read(4)
            if magic != b"\x7fELF":
                raise RuntimeError(f"not an ELF binary: {path}")
            handle.seek(18)
            machine = struct.unpack("<H", handle.read(2))[0]
        if machine != 0xB7:
            raise RuntimeError(f"expected AArch64 ELF machine 0xB7, got 0x{machine:x}")

    def test(self):
        dep = self.dependencies["tinyice"]
        package_folder = dep.package_folder
        real_binary = os.path.join(package_folder, "libexec", "tinyice", "tinyice-real")
        wrapper = os.path.join(package_folder, "bin", "tinyice")

        self._assert_aarch64_elf(wrapper)
        self._assert_aarch64_elf(real_binary)

        if can_run(self):
            script = os.path.join(self.source_folder, "test_tinyice.sh")
            self.run(f'sh "{script}" "{wrapper}" "{real_binary}"', env="conanrun")
