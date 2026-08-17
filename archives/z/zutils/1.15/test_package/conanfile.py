#!/usr/bin/env python3
"""Conan test_package for zutils.

Tests that the installed zcat binary can decompress a gzip file
and that zcat --version reports the correct version.
"""
import os

from conan import ConanFile


class ZutilsTestConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        test_script = os.path.join(self.source_folder, "test_zutils.sh")
        self.run(f"bash {test_script}", env="conanrun")
