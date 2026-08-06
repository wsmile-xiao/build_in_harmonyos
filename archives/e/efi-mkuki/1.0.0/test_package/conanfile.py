#!/usr/bin/env python3
"""Conan test_package for efi-mkuki — smoke test the installed script.

Verifies that efi-mkuki is installed, executable, and outputs the
correct version string when run with -V.
"""
import os

from conan import ConanFile


class EfiMkukiTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg_folder = self.dependencies["efi-mkuki"].package_folder
        bin_dir = os.path.join(pkg_folder, "bin")
        # R34: exercise the packaged artifact — run efi-mkuki -V
        self.run(f"bash {os.path.join(os.path.dirname(__file__), 'test_efi_mkuki.sh')} {bin_dir}", env="conanrun")
        self.output.info("efi-mkuki: smoke test passed")
