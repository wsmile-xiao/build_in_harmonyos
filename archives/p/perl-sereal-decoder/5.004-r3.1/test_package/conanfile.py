#!/usr/bin/env python3
"""Conan test_package — perl-sereal-decoder 5.004-r3.1 (Sereal::Decoder)

Tests that Sereal::Decoder package contains expected files and Perl syntax is valid.
On OHOS/HMDFS, .so runtime loading in conan cache is blocked by file permission
model (E046). This test uses file verification + perl -c syntax check, which is
the standard approach for Perl XS modules on OHOS.
"""
import glob
import os
import subprocess

from conan import ConanFile


class PerlSerealDecoderTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["perl-sereal-decoder"]
        pkg_folder = pkg.package_folder

        # Run shell test script with package folder as argument
        # test.sh verifies: Decoder.pm/Constants.pm/Decoder.so existence +
        # ELF format + .codesign section + module declaration
        test_script = os.path.join(self.recipe_folder, "test.sh")
        self.run(f'bash "{test_script}" "{pkg_folder}"', env="conanrun")

        # Additional Python-level verification for critical assertions
        pm_files = glob.glob(os.path.join(pkg_folder, "**", "Decoder.pm"), recursive=True)
        if not pm_files:
            raise AssertionError("Decoder.pm not found in package")
        self.output.info(f"Decoder.pm found at {pm_files[0]}")

        const_files = glob.glob(os.path.join(pkg_folder, "**", "Constants.pm"), recursive=True)
        if not const_files:
            raise AssertionError("Constants.pm not found in package")
        self.output.info(f"Constants.pm found at {const_files[0]}")

        so_files = glob.glob(os.path.join(pkg_folder, "**", "Decoder.so"), recursive=True)
        if not so_files:
            raise AssertionError("Decoder.so not found in package (XS compilation may have failed)")
        self.output.info(f"Decoder.so found at {so_files[0]}")

        # Perl syntax check (does not trigger .so dlopen)
        self.run(f'perl -c "{pm_files[0]}"', env="conanrun")
        self.output.info("Decoder.pm syntax check passed")

        self.run(f'perl -c "{const_files[0]}"', env="conanrun")
        self.output.info("Constants.pm syntax check passed")

        # Check file sizes
        pm_size = os.path.getsize(pm_files[0])
        so_size = os.path.getsize(so_files[0])
        self.output.info(f"Decoder.pm: {pm_size} bytes")
        self.output.info(f"Decoder.so: {so_size} bytes (ELF aarch64, self-signed)")
