#!/usr/bin/env python3
"""Conan test_package for psftools 1.0.14 — terminal tools smoke test.

Verifies that installed binaries exist and are valid ELF files.
(ELF signing restriction on HarmonyOS prevents direct execution.)
"""
import os
import struct

from conan import ConanFile


class PsftoolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Locate the package folder
        pkg_folder = self.dependencies["psftools"].package_folder
        bin_dir = os.path.join(pkg_folder, "bin")

        # Key binaries to verify
        binaries = [
            "psf2txt", "txt2psf", "psfmerge", "psfjoin",
            "psf2bdf", "psf2raw", "raw2psf", "psfxform",
            "cpi2psf", "cpicomp", "cpidcomp", "wof2psf",
            "fnt2psf", "fon2fnts", "zx2psf", "wyse2psf"
        ]

        for binary in binaries:
            bin_path = os.path.join(bin_dir, binary)
            assert os.path.exists(bin_path), f"Binary not found: {binary}"

            # Verify it's a valid ELF file
            with open(bin_path, "rb") as f:
                magic = f.read(4)
                assert magic == b'\x7fELF', f"{binary} is not a valid ELF file (magic: {magic})"

            self.output.info(f"✅ {binary}: valid ELF binary")

        self.output.info("All psftools binaries verified successfully")
