#!/usr/bin/env python3
"""Conan test_package for lynis — shell script tool L1 test.

Tests that the lynis script is installed, syntactically valid, and runs correctly.
"""
import os
import shutil

from conan import ConanFile


class LynisTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find lynis binary in the installed package
        lynis_pkg = self.dependencies["lynis"]
        lynis_bin = os.path.join(lynis_pkg.package_folder, "bin", "lynis")
        if not os.path.exists(lynis_bin):
            raise Exception(f"lynis binary not found at {lynis_bin}")
        # Verify syntax
        self.run(f"sh -n {lynis_bin}", env="conanrun")
        # Actually run lynis --version to verify the script executes (R34)
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        self.run(f"{bash} {lynis_bin} --version", env="conanrun")
        print(f"lynis test: PASS ({lynis_bin})")
