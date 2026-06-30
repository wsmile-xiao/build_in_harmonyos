#!/usr/bin/env python3
"""Conan test_package for vmdktool 1.4.

Verifies that the vmdktool binary exists in the package and is a valid ELF.
Due to ELF signature restrictions on OpenHarmony, we cannot execute the binary
directly in the test environment, so we verify its existence and ELF format.
"""
import os
import struct

from conan import ConanFile


class VmdktoolTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        pass  # No build step needed — we just verify the package

    def test(self):
        pkg_folder = self.dependencies["vmdktool"].package_folder
        bin_path = os.path.join(pkg_folder, "bin", "vmdktool")

        # Verify binary exists
        assert os.path.isfile(bin_path), f"vmdktool binary not found at {bin_path}"
        self.output.info(f"Found vmdktool binary: {bin_path}")

        # Verify it's a valid ELF file (magic bytes)
        with open(bin_path, "rb") as f:
            magic = f.read(4)
            assert magic == b'\x7fELF', f"Invalid ELF magic: {magic}"
            self.output.info("ELF magic check: PASS")

            # Verify it's 64-bit
            f.seek(4)
            ei_class = struct.unpack("B", f.read(1))[0]
            assert ei_class == 2, f"Expected 64-bit ELF (class=2), got class={ei_class}"
            self.output.info("ELF 64-bit check: PASS")

            # Verify it's AArch64
            f.seek(18)
            e_machine = struct.unpack("<H", f.read(2))[0]
            assert e_machine == 183, f"Expected AArch64 (machine=183), got machine={e_machine}"
            self.output.info("ELF AArch64 check: PASS")

        self.output.success("vmdktool 1.4 smoke test: ALL CHECKS PASSED")
