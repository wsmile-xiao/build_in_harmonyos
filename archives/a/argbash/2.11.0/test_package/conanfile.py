#!/usr/bin/env python3
"""Conan test_package for argbash 2.11.0 — verifies the argbash binary works.

Tests that the argbash executable can:
1. Report its version (smoke test)
2. Generate a bash script from an m4 template (functional test)
3. Run the generated script with arguments (end-to-end test)

R34: test must substantially depend on the tested package by executing
its binary and validating output.
"""
import os

from conan import ConanFile


class ArgbashTestConan(ConanFile):
    settings = "os", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Use the package's argbash binary from package_folder, not system PATH
        dep = self.dependencies["argbash"]
        bin_dir = os.path.join(dep.package_folder, "bin")
        # OHOS: use bash wrapper for reliable execution
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        self.run(f"{bash} test.sh {bin_dir}", env="conanrun")
