#!/usr/bin/env python3
"""Conan test_package for nxp-mfgtools (uuu).

Verifies the uuu binary is properly built and installed in the package.
Uses test_uuu.sh to verify:
  - Binary exists in package bindirs
  - Binary is a valid ELF file
  - Binary can be invoked (uuu -h)
  - libusb_init failure on platforms without USB is expected (not a build issue)
"""
import os

from conan import ConanFile


class NxpmfgtoolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["nxp-mfgtools"]
        bin_path = None
        for bindir in dep.cpp_info.bindirs:
            full_path = os.path.join(dep.package_folder, bindir, "uuu")
            if os.path.isfile(full_path):
                bin_path = full_path
                break

        if not bin_path:
            raise Exception("uuu binary not found in package bindirs")

        self.output.info(f"uuu binary found: {bin_path}")

        # Run the test script to verify binary
        test_script = os.path.join(self.source_folder, "test_uuu.sh")
        self.run(f'bash "{test_script}" "{bin_path}"')
