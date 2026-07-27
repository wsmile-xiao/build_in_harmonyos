#!/usr/bin/env python3
"""Conan test_package for chibi-scheme 0.12.

Verifies that the chibi-scheme binary is installed and runs correctly.
chibi-scheme is a Scheme interpreter with a C embedding API.
"""
import os

from conan import ConanFile


class ChibiSchemeTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if self.settings.os not in ("Linux", "OHOS"):
            return

        pkg_folder = self.dependencies["chibi-scheme"].package_folder
        chibi_bin = os.path.join(pkg_folder, "bin", "chibi-scheme")

        assert os.path.isfile(chibi_bin), f"chibi-scheme binary not found at {chibi_bin}"

        # Set module path so chibi-scheme can find init-7.scm and runtime files
        share_chibi = os.path.join(pkg_folder, "share", "chibi")
        lib_chibi = os.path.join(pkg_folder, "lib", "chibi")
        lib_dir = os.path.join(pkg_folder, "lib")

        self.run(
            f'CHIBI_MODULE_PATH="{share_chibi}:{lib_chibi}" '
            f'LD_LIBRARY_PATH="{lib_dir}" '
            f'{chibi_bin} -e "(display (+ 1 2))(newline)"'
        )
