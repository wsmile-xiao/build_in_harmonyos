#!/usr/bin/env python3
"""Conan test_package for osinfo-db — verifies data file installation.

osinfo-db is a pure data package (XML/JSON files). This test verifies
that the data files are correctly installed in the package's resdirs.
"""
import os

from conan import ConanFile


class OsinfoDBTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["osinfo-db"]
        osinfo_dir = os.path.join(pkg.package_folder, "share", "osinfo")
        script = os.path.join(self.source_folder, "verify_data.sh")
        self.run(f"bash {script} {osinfo_dir}")
