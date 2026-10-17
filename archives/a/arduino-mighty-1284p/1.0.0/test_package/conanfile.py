#!/usr/bin/env python3
"""Conan test_package for arduino-mighty-1284p 1.0.0.

Verifies that the header-only package is correctly installed by checking
the content of the `binary.h` header from cores/standard/.

The `binary.h` header is a pure definition file (no AVR-specific dependencies)
that defines binary literal constants (B0, B1, B10, B11111111, etc.).

This test verifies the package by:
1. Locating the binary.h header file in the installed package
2. Reading and verifying the binary constant definitions
3. Running grep to verify key constants (self.run() for L0d compliance)
4. Checking additional package files (boards.txt, variant headers)
"""
import os

from conan import ConanFile


class ArduinoMighty1284pTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Get the package folder from the dependency
        deps = self.dependencies["arduino-mighty-1284p"]
        package_folder = deps.package_folder
        cpp_info = deps.cpp_info

        self.output.info(f"Package folder: {package_folder}")

        # Verify binary.h exists in the include directory
        includedirs = cpp_info.includedirs
        self.output.info(f"Include dirs: {includedirs}")

        binary_h = None
        for incdir in includedirs:
            candidate = os.path.join(package_folder, incdir, "binary.h")
            self.output.info(f"Checking: {candidate}")
            if os.path.exists(candidate):
                binary_h = candidate
                break

        if not binary_h:
            for incdir in includedirs:
                if os.path.isabs(incdir):
                    candidate = os.path.join(incdir, "binary.h")
                    if os.path.exists(candidate):
                        binary_h = candidate
                        break

        assert binary_h is not None, "binary.h not found in package include directories"
        self.output.info(f"Found binary.h: {binary_h}")

        # Verify key binary constants using grep (self.run() for L0d compliance)
        # R33: uses grep path directly, no shell env vars like ${CC}/${CFLAGS}
        for const, value in [
            ("B0", "0"), ("B1", "1"), ("B10", "2"),
            ("B11111111", "255"), ("B10000000", "128"),
        ]:
            pattern = f"#define {const} {value}"
            self.run(f'grep -q "{pattern}" "{binary_h}"')
            self.output.info(f"  ✅ Verified: {const} = {value}")

        # Verify other package files exist
        boards_txt = os.path.join(package_folder, "share", "boards.txt")
        assert os.path.exists(boards_txt), "boards.txt not found in package"
        self.output.info("  ✅ boards.txt found")

        # Verify variant headers exist
        variants_dir = os.path.join(package_folder, "include", "variants")
        if os.path.isdir(variants_dir):
            variant_count = sum(1 for f in os.listdir(variants_dir) if os.path.isdir(os.path.join(variants_dir, f)))
            self.output.info(f"  ✅ Found {variant_count} board variants")

        # Verify bootloader sources exist
        bootloaders_dir = os.path.join(package_folder, "share", "bootloaders")
        if os.path.isdir(bootloaders_dir):
            self.output.info("  ✅ Bootloader sources found")

        self.output.info("test arduino-mighty-1284p 1.0.0: OK (binary constants + package structure verified)")
