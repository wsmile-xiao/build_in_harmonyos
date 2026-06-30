#!/usr/bin/env python3
"""Conan test_package — wla-dx 10.6 (terminal tool, binary verification).

wla-dx produces only executables (no libraries).
This test verifies that installed binaries exist and are valid ELF files.
"""
import os

from conan import ConanFile


class WlaDxTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # No build needed for binary-only package
        pass

    def test(self):
        # Verify the binary exists in the package
        bin_dir = os.path.join(self.dependencies["wla-dx"].package_folder, "bin")
        # Check at least one key binary
        wla_gb = os.path.join(bin_dir, "wla-gb")
        assert os.path.isfile(wla_gb), f"wla-gb not found at {wla_gb}"
        # Verify it's a valid ELF file
        import struct
        with open(wla_gb, "rb") as f:
            magic = f.read(4)
            assert magic == b"\x7fELF", f"wla-gb is not a valid ELF file (magic: {magic})"
        self.output.info(f"✅ wla-gb verified: valid ELF at {wla_gb}")
