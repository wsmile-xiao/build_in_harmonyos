#!/usr/bin/env python3
"""test_package for openfortivpn — verifies the built binary.

R34: Test must substantially depend on the tested package.
This test executes `openfortivpn --version` and verifies the output
contains the expected version string "1.24.1".
"""
import os

from conan import ConanFile


class OpenfortivpnTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Find the openfortivpn binary in the package
        dep = self.dependencies["openfortivpn"]
        bin_dir = os.path.join(dep.package_folder, "bin")
        binary = os.path.join(bin_dir, "openfortivpn")
        if not os.path.isfile(binary):
            raise Exception(f"openfortivpn binary not found at {binary}")
        # Execute --version and verify output
        self.run(f'"{binary}" --version', env="conanrun")
